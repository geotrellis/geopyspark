package geopyspark.geotrellis

import geopyspark.geotrellis._
import geopyspark.geotrellis.GeoTrellisUtils._

import protos.tileMessages._
import protos.tupleMessages._

import geotrellis.proj4._
import geotrellis.raster._
import geotrellis.raster.distance._
import geotrellis.raster.io.geotiff._
import geotrellis.raster.io.geotiff.compression._
import geotrellis.raster.mapalgebra.local._
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
import scala.collection.mutable.ArrayBuffer

import spire.syntax.cfor._


abstract class TiledRasterLayer[K: SpatialComponent: JsonFormat: ClassTag: Boundable] extends TileLayer[K] with Serializable {
  import Constants._

  type keyType = K

  def rdd: RDD[(K, MultibandTile)] with Metadata[TileLayerMetadata[K]]
  def zoomLevel: Option[Int]

  def repartition(partitioner: Partitioner): TiledRasterLayer[K] =
    withRDD(rdd.partitionBy(partitioner))

  def repartition(numPartitions: Int): TiledRasterLayer[K] =
    withRDD(rdd.repartition(numPartitions))

  def bands(band: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { multibandTile => multibandTile.subsetBands(band) })

  def bands(bands: java.util.ArrayList[Int]): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { multibandTile => multibandTile.subsetBands(bands.asScala) })

  def getZoom: Integer =
    zoomLevel match {
      case None => null
      case Some(z) => new Integer(z)
    }

  /** Encode RDD as Avro bytes and return it with avro schema used */
  def toProtoRDD(): JavaRDD[Array[Byte]]

  def collectKeys(): java.util.ArrayList[Array[Byte]]

  def layerMetadata: String = rdd.metadata.toJson.prettyPrint

  def mask(wkbs: java.util.ArrayList[Array[Byte]]): TiledRasterLayer[K] = {
    val geometries: Seq[MultiPolygon] = wkbs
      .asScala.map({ wkb => WKB.read(wkb) })
      .flatMap({
        case p: Polygon => Some(MultiPolygon(p))
        case m: MultiPolygon => Some(m)
        case _ => None
      })
    mask(geometries)
  }

  protected def mask(geometries: Seq[MultiPolygon]): TiledRasterLayer[K]

  protected def reproject(target_crs: String, resampleMethod: ResampleMethod): TiledRasterLayer[K]
  protected def reproject(target_crs: String, layoutType: LayoutType, resampleMethod: ResampleMethod): TiledRasterLayer[K]
  def reproject(targetCRS: String, layoutDefinition: LayoutDefinition, resampleMethod: ResampleMethod): TiledRasterLayer[K]

  def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: ResampleMethod
  ): TiledRasterLayer[K] =
    tileToLayout(layoutDefinition, None, resampleMethod)

  def tileToLayout(
    layoutType: LayoutType,
    resampleMethod: ResampleMethod
  ): TiledRasterLayer[K] = {
    val (layoutDefinition, zoom) =
      layoutType.layoutDefinitionWithZoom(rdd.metadata.crs, rdd.metadata.extent, rdd.metadata.cellSize)

    tileToLayout(layoutDefinition, zoom, resampleMethod)
  }

  def tileToLayout(
    layOutDefinition: LayoutDefinition,
    zoom: Option[Int],
    resampleMethod: ResampleMethod
  ): TiledRasterLayer[K]

  def pyramid(resampleMethod: ResampleMethod, partitioner: Partitioner): Array[_] // Array[TiledRasterLayer[K]]

  def focal(
    operation: String,
    neighborhood: String,
    param1: Double,
    param2: Double,
    param3: Double,
    partitioner: Partitioner
  ): TiledRasterLayer[K]

  def slope(zFactorCalculator: ZFactorCalculator): TiledRasterLayer[K]

  def costDistance(
    sc: SparkContext,
    wkbs: java.util.ArrayList[Array[Byte]],
    maxDistance: Double
  ): TiledRasterLayer[K] = {
    val geometries = wkbs.asScala.map({ wkb => WKB.read(wkb) })

    costDistance(sc, geometries, maxDistance)
  }

  protected def costDistance(
    sc: SparkContext,
    geometries: Seq[Geometry],
    maxDistance: Double
  ): TiledRasterLayer[K]

  def hillshade(sc: SparkContext,
    azimuth: Double,
    altitude: Double,
    zFactor: Double,
    band: Int
  ): TiledRasterLayer[K]

  def localMax(i: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map(_.localMax(i))) })

  def localMax(d: Double): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map(_.localMax(d))) })

  def localMax(other: TiledRasterLayer[K]): TiledRasterLayer[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map { case (b1, b2) => Max(b1, b2) }
        MultibandTile(tiles)
      }
    })

  def localAdd(i: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y + i }) })

  def localAdd(d: Double): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y + d }) })

  def localAdd(other: TiledRasterLayer[K]): TiledRasterLayer[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map { case (b1, b2) => b1 + b2 }
        MultibandTile(tiles)
      }
    })

  def localAdd(others: ArrayList[TiledRasterLayer[K]]): TiledRasterLayer[K] =
    withRDD(rdd.combineValues(others.asScala.map(_.rdd)) { ts =>
      val bandCount = ts.head.bandCount
      val newBands = Array.ofDim[Tile](bandCount)
      cfor(0)(_ < bandCount, _ + 1) { b =>
        newBands(b) = ts.map(_.band(b)).localAdd
      }
      MultibandTile(newBands)
    })

  def localSubtract(i: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y - i }) })

  def reverseLocalSubtract(i: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y.-:(i) }) })

  def localSubtract(d: Double): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y - d }) })

  def reverseLocalSubtract(d: Double): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y.-:(d) }) })

  def localSubtract(other: TiledRasterLayer[K]): TiledRasterLayer[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map(tup => tup._1 - tup._2)
        MultibandTile(tiles)
      }
    })

  def localMultiply(i: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y * i }) })

  def localMultiply(d: Double): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y * d }) })

  def localMultiply(other: TiledRasterLayer[K]): TiledRasterLayer[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map(tup => tup._1 * tup._2)
        MultibandTile(tiles)
      }
    })

  def localDivide(i: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y / i }) })

  def localDivide(d: Double): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y / d }) })

  def reverseLocalDivide(i: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y./:(i) }) })

  def reverseLocalDivide(d: Double): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y./:(d) }) })

  def localDivide(other: TiledRasterLayer[K]): TiledRasterLayer[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map(tup => tup._1 / tup._2)
        MultibandTile(tiles)
      }
    })

  def localAbs(): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y.localAbs() }) })

  def localPow(i: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y ** i }) })

  def localPow(d: Double): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y ** d }) })

  def localPow(other: TiledRasterLayer[K]): TiledRasterLayer[K] =
    withRDD(rdd.combineValues(other.rdd) {
      case (x: MultibandTile, y: MultibandTile) => {
        val tiles: Vector[Tile] =
          x.bands.zip(y.bands).map(tup => tup._1 ** tup._2)
        MultibandTile(tiles)
      }
    })

  def reverseLocalPow(i: Int): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y.localPowValue(i) }) })

  def reverseLocalPow(d: Double): TiledRasterLayer[K] =
    withRDD(rdd.mapValues { x => MultibandTile(x.bands.map { y => y.localPowValue(d) }) })

  def convertDataType(newType: String): TiledRasterLayer[_] =
    withContextRDD(rdd.convert(CellType.fromName(newType)).asInstanceOf[ContextRDD[K, MultibandTile, TileLayerMetadata[K]]])

  def normalize(oldMin: Double, oldMax: Double, newMin: Double, newMax: Double): TiledRasterLayer[K] =
    withRDD {
      rdd.mapValues { tile =>
        MultibandTile {
          tile.bands.map { band =>
            band.normalize(oldMin, oldMax, newMin, newMax)
          }
        }
      }
    }

  def polygonalMin(geom: Array[Byte]): Array[Int] =
    WKB.read(geom) match {
      case poly: Polygon => rdd.polygonalMin(poly)
      case multi: MultiPolygon => rdd.polygonalMin(multi)
    }

  def polygonalMinDouble(geom: Array[Byte]): Array[Double] =
    WKB.read(geom) match {
      case poly: Polygon => rdd.polygonalMinDouble(poly)
      case multi: MultiPolygon => rdd.polygonalMinDouble(multi)
    }

  def polygonalMax(geom: Array[Byte]): Array[Int] =
    WKB.read(geom) match {
      case poly: Polygon => rdd.polygonalMax(poly)
      case multi: MultiPolygon => rdd.polygonalMax(multi)
    }

  def polygonalMaxDouble(geom: Array[Byte]): Array[Double] =
    WKB.read(geom) match {
      case poly: Polygon => rdd.polygonalMaxDouble(poly)
      case multi: MultiPolygon => rdd.polygonalMaxDouble(multi)
    }

  def polygonalMean(geom: Array[Byte]): Array[Double] =
    WKB.read(geom) match {
      case poly: Polygon => rdd.polygonalMean(poly)
      case multi: MultiPolygon => rdd.polygonalMean(multi)
    }

  def polygonalSum(geom: Array[Byte]): Array[Long] =
    WKB.read(geom) match {
      case poly: Polygon => rdd.polygonalSum(poly)
      case multi: MultiPolygon => rdd.polygonalSum(multi)
    }

  def polygonalSumDouble(geom: Array[Byte]): Array[Double] =
    WKB.read(geom) match {
      case poly: Polygon => rdd.polygonalSumDouble(poly)
      case multi: MultiPolygon => rdd.polygonalSumDouble(multi)
    }

  def tobler(): TiledRasterLayer[K] = withRDD {
    rdd.withContext { rdd =>
      rdd.mapValues { bands =>
        bands.mapBands { (i, tile) =>
          tile.mapDouble { z =>
            val radians = z * math.Pi / 180.0
            val m = math.tan(radians)
            6 * (math.pow(math.E, (-3.5 * math.abs(m + 0.05))))
          }
        }
      }
    }
  }

  def aggregateByCell(operation: String): TiledRasterLayer[K] = {
    val bands: RDD[(K, Array[ArrayBuffer[Tile]])] =
      rdd.combineByKey(
        (multi: MultibandTile) => {
          val arr = Array.ofDim[ArrayBuffer[Tile]](multi.bandCount)

          cfor(0)(_ < arr.size, _ + 1) { x =>
            arr(x) = ArrayBuffer(multi.band(x))
          }

          arr
        },
        (acc: Array[ArrayBuffer[Tile]], multi: MultibandTile) =>
          acc.zip(multi.bands.toBuffer).map {
            case (arr: ArrayBuffer[Tile], tile: Tile) => tile +=: arr
          },
        (acc1: Array[ArrayBuffer[Tile]], acc2: Array[ArrayBuffer[Tile]]) =>
          acc1.zip(acc2) map { case (x, y) => x ++=: y }
        )

    val result: RDD[(K, Array[Tile])] =
      operation match {
        case SUM => bands.mapValues { x => x.map { tiles => tiles.reduce( _ localAdd _ ) } }
        case MIN => bands.mapValues { x => x.map(Min(_)) }
        case MAX => bands.mapValues { x => x.map(Max(_)) }
        case MEAN => bands.mapValues { x => x.map(Mean(_)) }
        case VARIANCE => bands.mapValues { x => x.map(Variance(_)) }
        case STANDARDDEVIATION => bands.mapValues { x => x.map { tiles => Sqrt(Variance(tiles)) } }
      }

    withRDD(result.mapValues { tiles => MultibandTile(tiles) } )
  }

  def merge(partitioner: Partitioner): TiledRasterLayer[K] =
    partitioner match {
      case p: Partitioner =>
        withRDD(
          ContextRDD(
            rdd
              .asInstanceOf[RDD[(K, MultibandTile)]]
              .merge(Some(p)),
              rdd.metadata
          )
        )
      case null => withRDD(ContextRDD(rdd.asInstanceOf[RDD[(K, MultibandTile)]].merge(), rdd.metadata))
    }

  def isFloatingPointLayer(): Boolean = rdd.metadata.cellType.isFloatingPoint

  protected def withRDD(result: RDD[(K, MultibandTile)]): TiledRasterLayer[K]

  def withContextRDD(result: ContextRDD[K, MultibandTile, TileLayerMetadata[K]]): TiledRasterLayer[K]
}
