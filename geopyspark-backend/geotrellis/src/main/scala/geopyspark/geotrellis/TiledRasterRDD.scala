package geopyspark.geotrellis

import geopyspark.geotrellis.GeoTrellisUtils._

import geotrellis.proj4._
import geotrellis.raster._
import geotrellis.raster.io.geotiff._
import geotrellis.raster.distance._
import geotrellis.raster.histogram._
import geotrellis.raster.rasterize._
import geotrellis.raster.render._
import geotrellis.raster.resample.ResampleMethod
import geotrellis.spark._
import geotrellis.spark.costdistance.IterativeCostDistance
import geotrellis.spark.io._
import geotrellis.spark.io.avro._
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
import geotrellis.vector.io.wkt.WKT
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


abstract class TiledRasterRDD[K: SpatialComponent: AvroRecordCodec: JsonFormat: ClassTag] extends TileRDD[K] {
  import Constants._

  type keyType = K

  def rdd: RDD[(K, MultibandTile)] with Metadata[TileLayerMetadata[K]]
  def zoomLevel: Option[Int]

  def repartition(numPartitions: Int): TiledRasterRDD[K] =
    withRDD(rdd.repartition(numPartitions))

  def getZoom: Integer =
    zoomLevel match {
      case None => null
      case Some(z) => new Integer(z)
    }

  /** Encode RDD as Avro bytes and return it with avro schema used */
  def toAvroRDD(): (JavaRDD[Array[Byte]], String) = PythonTranslator.toPython(rdd)

  def layerMetadata: String = rdd.metadata.toJson.prettyPrint

  def mask(wkts: java.util.ArrayList[String]): TiledRasterRDD[K] = {
    val geometries: Seq[MultiPolygon] = wkts
      .asScala.map({ wkt => WKT.read(wkt) })
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
    resampleMethod: String
  ): TiledRasterRDD[K] = {
    val layoutDefinition = Right(LayoutDefinition(extent.toExtent, layout.toTileLayout))

    reproject(layoutDefinition, TileRDD.getCRS(crs).get, getReprojectOptions(resampleMethod))
  }

  def reproject(
    scheme: String,
    tileSize: Int,
    resolutionThreshold: Double,
    crs: String,
    resampleMethod: String
  ): TiledRasterRDD[K] = {
    val _crs = TileRDD.getCRS(crs).get

    val layoutScheme =
      scheme match {
        case FLOAT => FloatingLayoutScheme(tileSize)
        case ZOOM => ZoomedLayoutScheme(_crs, tileSize, resolutionThreshold)
      }

    reproject(Left(layoutScheme), _crs, getReprojectOptions(resampleMethod))
  }

  protected def reproject(
    layout: Either[LayoutScheme, LayoutDefinition],
    crs: CRS,
    options: Reproject.Options
  ): TiledRasterRDD[K]

  def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: String
  ): TiledRasterRDD[K]

  def pyramid(
    startZoom: Int,
    endZoom: Int,
    resampleMethod: String
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
    wkts: java.util.ArrayList[String],
    maxDistance: Double
  ): TiledRasterRDD[K] = {
    val geometries = wkts.asScala.map({ wkt => WKT.read(wkt) })

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

  def convertDataType(newType: String): TiledRasterRDD[K] =
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

  def polygonalMin(geom: String): Int =
    WKT.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMin(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMin(multi)
    }

  def polygonalMinDouble(geom: String): Double =
    WKT.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMinDouble(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMinDouble(multi)
    }

  def polygonalMax(geom: String): Int =
    WKT.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMax(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMax(multi)
    }

  def polygonalMaxDouble(geom: String): Double =
    WKT.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMaxDouble(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMaxDouble(multi)
    }

  def polygonalMean(geom: String): Double =
    WKT.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalMean(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalMean(multi)
    }

  def polygonalSum(geom: String): Long =
    WKT.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalSum(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalSum(multi)
    }

  def polygonalSumDouble(geom: String): Double =
    WKT.read(geom) match {
      case poly: Polygon => singleTileLayerRDD.polygonalSumDouble(poly)
      case multi: MultiPolygon => singleTileLayerRDD.polygonalSumDouble(multi)
    }

  def isFloatingPointLayer(): Boolean = rdd.metadata.cellType.isFloatingPoint

  def getIntHistograms(): Histogram[Int] = rdd.histogramExactInt.head

  def getDoubleHistograms(): Histogram[Double] = rdd.histogram.head

  protected def withRDD(result: RDD[(K, MultibandTile)]): TiledRasterRDD[K]
}


class SpatialTiledRasterRDD(
  val zoomLevel: Option[Int],
  val rdd: RDD[(SpatialKey, MultibandTile)] with Metadata[TileLayerMetadata[SpatialKey]]
) extends TiledRasterRDD[SpatialKey] {

  def lookup(
    col: Int,
    row: Int
  ): (java.util.ArrayList[Array[Byte]], String) = {
    val tiles = rdd.lookup(SpatialKey(col, row))
    PythonTranslator.toPython(tiles)
  }

  def reproject(
    layout: Either[LayoutScheme, LayoutDefinition],
    crs: CRS,
    options: Reproject.Options
  ): TiledRasterRDD[SpatialKey] = {
    val (zoom, reprojected) = TileRDDReproject(rdd, crs, layout, options)
    SpatialTiledRasterRDD(Some(zoom), reprojected)
  }

  def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: String
  ): TiledRasterRDD[SpatialKey] = {
    val method: ResampleMethod = TileRDD.getResampleMethod(resampleMethod)
    val mapKeyTransform =
      MapKeyTransform(
        layoutDefinition.extent,
        layoutDefinition.layoutCols,
        layoutDefinition.layoutRows)

    val crs = rdd.metadata.crs
    val projectedRDD = rdd.map{ x => (ProjectedExtent(mapKeyTransform(x._1), crs), x._2) }
    val retiledLayerMetadata = rdd.metadata.copy(
      layout = layoutDefinition,
      bounds = KeyBounds(mapKeyTransform(rdd.metadata.extent))
    )

    val tileLayer =
      MultibandTileLayerRDD(projectedRDD.tileToLayout(retiledLayerMetadata, method), retiledLayerMetadata)

    SpatialTiledRasterRDD(None, tileLayer)
  }

  def pyramid(
    startZoom: Int,
    endZoom: Int,
    resampleMethod: String
  ): Array[TiledRasterRDD[SpatialKey]] = {
    require(! rdd.metadata.bounds.isEmpty, "Can not pyramid an empty RDD")

    val method: ResampleMethod = TileRDD.getResampleMethod(resampleMethod)
    val scheme = ZoomedLayoutScheme(rdd.metadata.crs, rdd.metadata.tileRows)
    val part = rdd.partitioner.getOrElse(new HashPartitioner(rdd.partitions.length))

    val leveledList =
      Pyramid.levelStream(
        rdd,
        scheme,
        startZoom,
        endZoom,
        Pyramid.Options(resampleMethod=method, partitioner=part)
      )

    leveledList.map{ x => SpatialTiledRasterRDD(Some(x._1), x._2) }.toArray
  }

  def focal(
    operation: String,
    neighborhood: String,
    param1: Double,
    param2: Double,
    param3: Double
  ): TiledRasterRDD[SpatialKey] = {
    val singleTileLayerRDD: TileLayerRDD[SpatialKey] = TileLayerRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    val _neighborhood = getNeighborhood(operation, neighborhood, param1, param2, param3)
    val cellSize = rdd.metadata.layout.cellSize
    val op: ((Tile, Option[GridBounds]) => Tile) = getOperation(operation, _neighborhood, cellSize, param1)

    val result: TileLayerRDD[SpatialKey] = FocalOperation(singleTileLayerRDD, _neighborhood)(op)

    val multibandRDD: MultibandTileLayerRDD[SpatialKey] =
      MultibandTileLayerRDD(result.mapValues{ x => MultibandTile(x) }, result.metadata)

    SpatialTiledRasterRDD(None, multibandRDD)
  }

  def mask(geometries: Seq[MultiPolygon]): TiledRasterRDD[SpatialKey] = {
    val options = Mask.Options.DEFAULT
    val singleBand = ContextRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )
    val result = Mask(singleBand, geometries, options)
    val multiBand = MultibandTileLayerRDD(
      result.mapValues({ v => MultibandTile(v) }),
      result.metadata
    )
    SpatialTiledRasterRDD(zoomLevel, multiBand)
  }

  def stitch: (Array[Byte], String) = {
    val contextRDD = ContextRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    PythonTranslator.toPython(contextRDD.stitch.tile)
  }

  def save_stitched(path: String): Unit =
    _save_stitched(path, None, None)

  def save_stitched(path: String, cropBounds: ArrayList[Double]): Unit =
    _save_stitched(path, Some(cropBounds), None)

  def save_stitched(path: String, cropBounds: ArrayList[Double], cropDimensions: ArrayList[Int]): Unit =
    _save_stitched(path, Some(cropBounds), Some(cropDimensions))

  private def _save_stitched(path: String, cropBounds: Option[ArrayList[Double]], cropDimensions: Option[ArrayList[Int]]): Unit = {

    val contextRDD = ContextRDD(
      rdd.map({ case (k, v) => (k, v.band(0)) }),
      rdd.metadata
    )
    val stitched: Raster[Tile] = contextRDD.stitch()

    val adjusted = {
      val cropExtent =
        cropBounds.map { b =>
          val bounds = b.asScala.toArray
          Extent(bounds(0), bounds(1), bounds(2), bounds(3))
        }

      val cropped =
        cropExtent match {
          case Some(extent) =>
            stitched.crop(extent)
          case None =>
            stitched
        }

      val resampled =
        cropDimensions.map(_.asScala.toArray) match {
          case Some(dimensions) =>
            cropped.resample(dimensions(0), dimensions(1))
          case None =>
            cropped
        }

      resampled
    }

    GeoTiff(adjusted, contextRDD.metadata.crs).write(path)
  }

  def costDistance(
    sc: SparkContext,
    geometries: Seq[Geometry],
    maxDistance: Double
  ): TiledRasterRDD[SpatialKey] = {
    val singleTileLayer = TileLayerRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    implicit def conversion(k: SpaceTimeKey): SpatialKey =
      k.spatialKey

    implicit val _sc = sc

    val result: TileLayerRDD[SpatialKey] =
      IterativeCostDistance(singleTileLayer, geometries, maxDistance)

    val multibandRDD: MultibandTileLayerRDD[SpatialKey] =
      MultibandTileLayerRDD(result.mapValues{ x => MultibandTile(x) }, result.metadata)

    SpatialTiledRasterRDD(None, multibandRDD)
  }

  def hillshade(
    sc: SparkContext, 
    azimuth: Double, 
    altitude: Double, 
    zFactor: Double, 
    band: Int
  ): TiledRasterRDD[SpatialKey] = {
    val tileLayer = TileLayerRDD(rdd.mapValues(_.band(band)), rdd.metadata)

    implicit val _sc = sc

    val result = tileLayer.hillshade(azimuth, altitude, zFactor)

    val multibandRDD: MultibandTileLayerRDD[SpatialKey] = 
      MultibandTileLayerRDD(result.mapValues{ tile => MultibandTile(tile) }, result.metadata)

    SpatialTiledRasterRDD(None, multibandRDD)
  }

  def reclassify(reclassifiedRDD: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def reclassifyDouble(reclassifiedRDD: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def withRDD(result: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(result, rdd.metadata))

  def toInt(converted: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toDouble(converted: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))
}


class TemporalTiledRasterRDD(
  val zoomLevel: Option[Int],
  val rdd: RDD[(SpaceTimeKey, MultibandTile)] with Metadata[TileLayerMetadata[SpaceTimeKey]]
) extends TiledRasterRDD[SpaceTimeKey] {

  def mask(geometries: Seq[MultiPolygon]): TiledRasterRDD[SpaceTimeKey] = {
    val options = Mask.Options.DEFAULT
    val singleBand = ContextRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )
    val result = Mask(singleBand, geometries, options)
    val multiBand = MultibandTileLayerRDD(
      result.mapValues({ v => MultibandTile(v) }),
      result.metadata
    )
    TemporalTiledRasterRDD(zoomLevel, multiBand)
  }

  def reproject(
    layout: Either[LayoutScheme, LayoutDefinition],
    crs: CRS,
    options: Reproject.Options
  ): TiledRasterRDD[SpaceTimeKey] = {
    val (zoom, reprojected) = TileRDDReproject(rdd, crs, layout, options)
    TemporalTiledRasterRDD(Some(zoom), reprojected)
  }

  def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: String
  ): TiledRasterRDD[SpaceTimeKey] = {
    val method: ResampleMethod = TileRDD.getResampleMethod(resampleMethod)
    val mapKeyTransform =
      MapKeyTransform(
        layoutDefinition.extent,
        layoutDefinition.layoutCols,
        layoutDefinition.layoutRows)

    val crs = rdd.metadata.crs

    val temporalRDD = rdd.map { x =>
      (TemporalProjectedExtent(mapKeyTransform(x._1), rdd.metadata.crs, x._1.instant), x._2)
    }

    val bounds = rdd.metadata.bounds.get
    val spatialBounds = KeyBounds(mapKeyTransform(rdd.metadata.extent))
    val retiledLayerMetadata = rdd.metadata.copy(
      layout = layoutDefinition,
      bounds = KeyBounds(
        minKey = bounds.minKey.setComponent[SpatialKey](spatialBounds.minKey),
        maxKey = bounds.maxKey.setComponent[SpatialKey](spatialBounds.maxKey)
      )
    )

    val tileLayer =
      MultibandTileLayerRDD(temporalRDD.tileToLayout(retiledLayerMetadata, method), retiledLayerMetadata)

    TemporalTiledRasterRDD(None, tileLayer)
  }

  def pyramid(
    startZoom: Int,
    endZoom: Int,
    resampleMethod: String
  ): Array[TiledRasterRDD[SpaceTimeKey]] = {
    require(! rdd.metadata.bounds.isEmpty, "Can not pyramid an empty RDD")

    val method: ResampleMethod = TileRDD.getResampleMethod(resampleMethod)
    val scheme = ZoomedLayoutScheme(rdd.metadata.crs, rdd.metadata.tileRows)
    val part = rdd.partitioner.getOrElse(new HashPartitioner(rdd.partitions.length))

    val leveledList =
      Pyramid.levelStream(
        rdd,
        scheme,
        startZoom,
        endZoom,
        Pyramid.Options(resampleMethod=method, partitioner=part)
      )

    leveledList.map{ x => TemporalTiledRasterRDD(Some(x._1), x._2) }.toArray
  }

  def focal(
    operation: String,
    neighborhood: String,
    param1: Double,
    param2: Double,
    param3: Double
  ): TiledRasterRDD[SpaceTimeKey] = {
    val singleTileLayerRDD: TileLayerRDD[SpaceTimeKey] = TileLayerRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    val _neighborhood = getNeighborhood(operation, neighborhood, param1, param2, param3)
    val cellSize = rdd.metadata.layout.cellSize
    val op: ((Tile, Option[GridBounds]) => Tile) = getOperation(operation, _neighborhood, cellSize, param1)

    val result: TileLayerRDD[SpaceTimeKey] = FocalOperation(singleTileLayerRDD, _neighborhood)(op)

    val multibandRDD: MultibandTileLayerRDD[SpaceTimeKey] =
      MultibandTileLayerRDD(result.mapValues{ x => MultibandTile(x) }, result.metadata)

    TemporalTiledRasterRDD(None, multibandRDD)
  }

  def costDistance(
    sc: SparkContext,
    geometries: Seq[Geometry],
    maxDistance: Double
  ): TiledRasterRDD[SpaceTimeKey] = {
    val singleTileLayer = TileLayerRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    implicit def convertion(k: SpaceTimeKey): SpatialKey =
      k.spatialKey

    implicit val _sc = sc

    val result: TileLayerRDD[SpaceTimeKey] =
      IterativeCostDistance(singleTileLayer, geometries, maxDistance)

    val multibandRDD: MultibandTileLayerRDD[SpaceTimeKey] =
      MultibandTileLayerRDD(result.mapValues{ x => MultibandTile(x) }, result.metadata)

    TemporalTiledRasterRDD(None, multibandRDD)
  }

  def hillshade(
    sc: SparkContext,
    azimuth: Double,
    altitude: Double,
    zFactor: Double,
    band: Int
  ): TiledRasterRDD[SpaceTimeKey] = {
    val tileLayer = TileLayerRDD(rdd.mapValues(_.band(band)), rdd.metadata)

    implicit val _sc = sc

    val result = tileLayer.hillshade(azimuth, altitude, zFactor)

    val multibandRDD: MultibandTileLayerRDD[SpaceTimeKey] = 
      MultibandTileLayerRDD(result.mapValues(MultibandTile(_)), result.metadata)

    TemporalTiledRasterRDD(None, multibandRDD)
  }

  def reclassify(reclassifiedRDD: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def reclassifyDouble(reclassifiedRDD: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def withRDD(result: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(result, rdd.metadata))

  def toInt(converted: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toDouble(converted: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))
}


object SpatialTiledRasterRDD {
  def fromAvroEncodedRDD(
    javaRDD: JavaRDD[Array[Byte]],
    schema: String,
    metadata: String
  ): SpatialTiledRasterRDD = {
    val md = metadata.parseJson.convertTo[TileLayerMetadata[SpatialKey]]
    val tileLayer = MultibandTileLayerRDD(PythonTranslator.fromPython[(SpatialKey, MultibandTile)](javaRDD, Some(schema)), md)

    SpatialTiledRasterRDD(None, tileLayer)
  }

  def apply(
    zoomLevel: Option[Int],
    rdd: RDD[(SpatialKey, MultibandTile)] with Metadata[TileLayerMetadata[SpatialKey]]
  ): SpatialTiledRasterRDD =
    new SpatialTiledRasterRDD(zoomLevel, rdd)

  def rasterize(
    sc: SparkContext,
    geometryString: String,
    extent: java.util.Map[String, Double],
    crs: String,
    cols: Int,
    rows: Int,
    fillValue: Int
  ): TiledRasterRDD[SpatialKey] = {
    val rasterExtent = RasterExtent(extent.toExtent, cols, rows)
    val projectedExtent = ProjectedExtent(rasterExtent.extent, TileRDD.getCRS(crs).get)

    val tile = Rasterizer.rasterizeWithValue(WKT.read(geometryString), rasterExtent, fillValue)
    val rdd = sc.parallelize(Array((projectedExtent, MultibandTile(tile))))

    val tileLayout = TileLayout(1, 1, cols, rows)
    val layoutDefinition = LayoutDefinition(rasterExtent.extent, tileLayout)

    val metadata = rdd.collectMetadata[SpatialKey](layoutDefinition)

    SpatialTiledRasterRDD(None, MultibandTileLayerRDD(rdd.tileToLayout(metadata), metadata))
  }

  def euclideanDistance(sc: SparkContext, geomWKT: String, geomCRSStr: String, cellTypeString: String, requestedZoom: Int): TiledRasterRDD[SpatialKey]= {
    val cellType = CellType.fromName(cellTypeString)
    val geom = geotrellis.vector.io.wkt.WKT.read(geomWKT)
    val srcCRS = TileRDD.getCRS(geomCRSStr).get
    val LayoutLevel(z, ld) = ZoomedLayoutScheme(srcCRS).levelForZoom(requestedZoom)
    val maptrans = ld.mapTransform
    val gb @ GridBounds(cmin, rmin, cmax, rmax) = maptrans(geom.envelope)

    val keys = for (r <- rmin to rmax; c <- cmin to cmax) yield SpatialKey(c, r)

    val pts =
      if (geom.isInstanceOf[MultiPoint]) {
        geom.asInstanceOf[MultiPoint].points.map(_.jtsGeom.getCoordinate)
      } else {
        val coords = collection.mutable.ListBuffer.empty[Coordinate]

        def createPoints(sk: SpatialKey) = {
          val ex = maptrans(sk)
          val re = RasterExtent(ex, ld.tileCols, ld.tileRows)

          def rasterizeToPoints(px: Int, py: Int): Unit = {
            val (x, y) = re.gridToMap(px, py)
            val coord = new Coordinate(x, y)
            coords += coord
          }

          Rasterizer.foreachCellByGeometry(geom, re)(rasterizeToPoints)
        }

        keys.foreach(createPoints)
        coords.toArray
      }

    val dt = KryoWrapper(DelaunayTriangulation(pts))
    val skRDD = sc.parallelize(keys)
    val mbtileRDD: RDD[(SpatialKey, MultibandTile)] = skRDD.mapPartitions({ skiter => skiter.map { sk =>
      val ex = maptrans(sk)
      val re = RasterExtent(ex, ld.tileCols, ld.tileRows)
      val tile = ArrayTile.empty(cellType, re.cols, re.rows)
      val vd = new VoronoiDiagram(dt.value, ex)
      vd.voronoiCellsWithPoints.foreach(EuclideanDistanceTile.rasterizeDistanceCell(re, tile)(_))
      (sk, MultibandTile(tile))
    } }, preservesPartitioning=true)

    val metadata = TileLayerMetadata(cellType, ld, maptrans(gb), srcCRS, KeyBounds(gb))

    SpatialTiledRasterRDD(Some(z), MultibandTileLayerRDD(mbtileRDD, metadata))
  }

}

object TemporalTiledRasterRDD {
  def fromAvroEncodedRDD(
    javaRDD: JavaRDD[Array[Byte]],
    schema: String,
    metadata: String
  ): TemporalTiledRasterRDD = {
    val md = metadata.parseJson.convertTo[TileLayerMetadata[SpaceTimeKey]]
    val tileLayer = MultibandTileLayerRDD(PythonTranslator.fromPython[(SpaceTimeKey, MultibandTile)](javaRDD, Some(schema)), md)

    TemporalTiledRasterRDD(None, tileLayer)
  }

  def apply(
    zoomLevel: Option[Int],
    rdd: RDD[(SpaceTimeKey, MultibandTile)] with Metadata[TileLayerMetadata[SpaceTimeKey]]
  ): TemporalTiledRasterRDD =
    new TemporalTiledRasterRDD(zoomLevel, rdd)

  def rasterize(
    sc: SparkContext,
    geometryString: String,
    extent: java.util.Map[String, Double],
    crs: String,
    instant: Int,
    cols: Int,
    rows: Int,
    fillValue: Int
  ): TiledRasterRDD[SpaceTimeKey] = {
    val rasterExtent = RasterExtent(extent.toExtent, cols, rows)
    val temporalExtent =
      TemporalProjectedExtent(rasterExtent.extent, TileRDD.getCRS(crs).get, instant.toInt)

    val tile = Rasterizer.rasterizeWithValue(WKT.read(geometryString), rasterExtent, fillValue)
    val rdd = sc.parallelize(Array((temporalExtent, MultibandTile(tile))))
    val tileLayout = TileLayout(1, 1, cols, rows)
    val layoutDefinition = LayoutDefinition(rasterExtent.extent, tileLayout)

    val metadata = rdd.collectMetadata[SpaceTimeKey](layoutDefinition)

    TemporalTiledRasterRDD(None, MultibandTileLayerRDD(rdd.tileToLayout(metadata), metadata))
  }

}
