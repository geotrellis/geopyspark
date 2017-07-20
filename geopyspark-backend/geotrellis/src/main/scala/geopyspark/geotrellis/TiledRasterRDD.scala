package geopyspark.geotrellis

import geopyspark.geotrellis._
import geopyspark.geotrellis.GeoTrellisUtils._

import protos.tileMessages._
import protos.tupleMessages._

import geotrellis.proj4._
import geotrellis.raster._
import geotrellis.raster.distance._
import geotrellis.raster.histogram._
import geotrellis.raster.io.geotiff._
import geotrellis.raster.io.geotiff.compression._
import geotrellis.raster.rasterize._
import geotrellis.raster.render._
import geotrellis.raster.resample.ResampleMethod
import geotrellis.spark._
import geotrellis.spark.costdistance.IterativeCostDistance
import geotrellis.spark.io._
import geotrellis.spark.io.json._
import geotrellis.spark.mapalgebra.local._
import geotrellis.spark.mapalgebra.focal._
import geotrellis.spark.mask.Mask
import geotrellis.spark.pyramid._
import geotrellis.spark.reproject._
import geotrellis.spark.tiling._
import geotrellis.spark.util._
import geotrellis.util._
import geotrellis.vector._
import geotrellis.vector.io.wkb.WKB
import geotrellis.vector.triangulation._
import geotrellis.vector.voronoi._

import spray.json._
import spray.json.DefaultJsonProtocol._
import spire.syntax.cfor._

import com.vividsolutions.jts.geom.Coordinate
import org.apache.spark._
import org.apache.spark.api.java.JavaRDD
import org.apache.spark.rdd._
import org.apache.spark.SparkContext._

import java.util.ArrayList
import scala.reflect._
import scala.collection.JavaConverters._


abstract class TiledRasterRDD[K: SpatialComponent: JsonFormat: ClassTag] extends TileRDD[K] {
  import Constants._

  type keyType = K

  def rdd: RDD[(K, MultibandTile)] with Metadata[TileLayerMetadata[K]]
  def zoomLevel: Option[Int]

  def repartition(numPartitions: Int): TiledRasterRDD[K] =
    withRDD(rdd.repartition(numPartitions))

  def bands(band: Int): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { multibandTile => multibandTile.subsetBands(band) })

  def bands(bands: java.util.ArrayList[Int]): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { multibandTile => multibandTile.subsetBands(bands.asScala) })

  def getZoom: Integer =
    zoomLevel match {
      case None => null
      case Some(z) => new Integer(z)
    }

  /** Encode RDD as Avro bytes and return it with avro schema used */
  def toProtoRDD(): JavaRDD[Array[Byte]]

  def resample_to_power_of_two(
    col_power: Int,
    row_power: Int,
    resampleMethod: ResampleMethod
  ): TiledRasterRDD[K]

  def layerMetadata: String = rdd.metadata.toJson.prettyPrint

  def mask(wkbs: java.util.ArrayList[Array[Byte]]): TiledRasterRDD[K] = {
    val geometries: Seq[MultiPolygon] = wkbs
      .asScala.map({ wkb => WKB.read(wkb) })
      .flatMap({
        case p: Polygon => Some(MultiPolygon(p))
        case m: MultiPolygon => Some(m)
        case _ => None
      })
    mask(geometries)
  }

  protected def mask(geometries: Seq[MultiPolygon]): TiledRasterRDD[K]

  def reproject(
    extent: java.util.Map[String, Double],
    layout: java.util.Map[String, Int],
    crs: String,
    resampleMethod: ResampleMethod
  ): TiledRasterRDD[K] = {
    val layoutDefinition = LayoutDefinition(extent.toExtent, layout.toTileLayout)

    reproject(layoutDefinition, TileRDD.getCRS(crs).get, getReprojectOptions(resampleMethod))
  }

  def reproject(
    layoutType: LayoutType,
    crs: String,
    resampleMethod: ResampleMethod
  ): TiledRasterRDD[K] = {
    val convertedCRS = TileRDD.getCRS(crs).get
    val layoutDefinition =
      layoutType.layoutDefinition(convertedCRS, rdd.metadata.extent, rdd.metadata.cellSize)

    reproject(layoutDefinition, convertedCRS, getReprojectOptions(resampleMethod))
  }

  protected def reproject(
    layout: LayoutDefinition,
    crs: CRS,
    options: Reproject.Options
  ): TiledRasterRDD[K]

  def tileToLayout(
    extent: java.util.Map[String, Double],
    tileLayout: java.util.Map[String, Int],
    resampleMethod: ResampleMethod
  ): TiledRasterRDD[K] =
    tileToLayout(
      LayoutDefinition(extent.toExtent, tileLayout.toTileLayout),
      resampleMethod)

  protected def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: ResampleMethod
  ): TiledRasterRDD[K]

  def pyramid(
    startZoom: Int,
    endZoom: Int,
    resampleMethod: ResampleMethod
  ): Array[_] // Array[TiledRasterRDD[K]]

  def focal(
    operation: String,
    neighborhood: String,
    param1: Double,
    param2: Double,
    param3: Double
  ): TiledRasterRDD[K]

  def costDistance(
    sc: SparkContext,
    wkbs: java.util.ArrayList[Array[Byte]],
    maxDistance: Double
  ): TiledRasterRDD[K] = {
    val geometries = wkbs.asScala.map({ wkb => WKB.read(wkb) })

    costDistance(sc, geometries, maxDistance)
  }

  protected def costDistance(
    sc: SparkContext,
    geometries: Seq[Geometry],
    maxDistance: Double
  ): TiledRasterRDD[K]

  def hillshade(sc: SparkContext,
    azimuth: Double,
    altitude: Double,
    zFactor: Double,
    band: Int
  ): TiledRasterRDD[K]

  def localAdd(i: Int): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y + i }) })

  def localAdd(d: Double): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y + d }) })

  def localAdd(other: TiledRasterRDD[K]): TiledRasterRDD[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map { case (b1, b2) => b1 + b2 }
        MultibandTile(tiles)
      }
    })

  def localAdd(others: ArrayList[TiledRasterRDD[K]]): TiledRasterRDD[K] =
    withRDD(rdd.combineValues(others.asScala.map(_.rdd)) { ts =>
      val bandCount = ts.head.bandCount
      val newBands = Array.ofDim[Tile](bandCount)
      cfor(0)(_ < bandCount, _ + 1) { b =>
        newBands(b) = ts.map(_.band(b)).localAdd
      }
      MultibandTile(newBands)
    })

  def localSubtract(i: Int): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y - i }) })

  def reverseLocalSubtract(i: Int): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y.-:(i) }) })

  def localSubtract(d: Double): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y - d }) })

  def reverseLocalSubtract(d: Double): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y.-:(d) }) })

  def localSubtract(other: TiledRasterRDD[K]): TiledRasterRDD[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map(tup => tup._1 - tup._2)
        MultibandTile(tiles)
      }
    })

  def localMultiply(i: Int): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y * i }) })

  def localMultiply(d: Double): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y * d }) })

  def localMultiply(other: TiledRasterRDD[K]): TiledRasterRDD[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map(tup => tup._1 * tup._2)
        MultibandTile(tiles)
      }
    })

  def localDivide(i: Int): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y / i }) })

  def localDivide(d: Double): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y / d }) })

  def reverseLocalDivide(i: Int): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y./:(i) }) })

  def reverseLocalDivide(d: Double): TiledRasterRDD[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y./:(d) }) })

  def localDivide(other: TiledRasterRDD[K]): TiledRasterRDD[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map(tup => tup._1 / tup._2)
        MultibandTile(tiles)
      }
    })

  def convertDataType(newType: String): TiledRasterRDD[_] =
    withRDD(rdd.convert(CellType.fromName(newType)))

  def normalize(oldMin: Double, oldMax: Double, newMin: Double, newMax: Double): TiledRasterRDD[K] =
    withRDD {
      rdd.mapValues { tile =>
        MultibandTile {
          tile.bands.map { band =>
            band.normalize(oldMin, oldMax, newMin, newMax)
          }
        }
      }
    }

  def singleTileLayerRDD: TileLayerRDD[K] = TileLayerRDD(
    rdd.mapValues({ v => v.band(0) }),
    rdd.metadata
  )

  def polygonalMin(geom: Array[Byte]): Int =
    WKB.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMin(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMin(multi)
    }

  def polygonalMinDouble(geom: Array[Byte]): Double =
    WKB.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMinDouble(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMinDouble(multi)
    }

  def polygonalMax(geom: Array[Byte]): Int =
    WKB.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMax(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMax(multi)
    }

  def polygonalMaxDouble(geom: Array[Byte]): Double =
    WKB.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMaxDouble(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMaxDouble(multi)
    }

  def polygonalMean(geom: Array[Byte]): Double =
    WKB.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMean(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMean(multi)
    }

  def polygonalSum(geom: Array[Byte]): Long =
    WKB.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalSum(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalSum(multi)
    }

  def polygonalSumDouble(geom: Array[Byte]): Double =
    WKB.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalSumDouble(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalSumDouble(multi)
    }

  def isFloatingPointLayer(): Boolean = rdd.metadata.cellType.isFloatingPoint

  def getIntHistograms(): Histogram[Int] = rdd.histogramExactInt.head

  def getDoubleHistograms(): Histogram[Double] = rdd.histogram.head

  protected def withRDD(result: RDD[(K, MultibandTile)]): TiledRasterRDD[K]
}
