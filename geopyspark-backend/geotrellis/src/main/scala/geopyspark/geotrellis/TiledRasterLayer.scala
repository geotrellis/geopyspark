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


abstract class TiledRasterLayer[K: SpatialComponent: JsonFormat: ClassTag] extends TileLayer[K] {
  import Constants._

  type keyType = K

  def rdd: RDD[(K, MultibandTile)] with Metadata[TileLayerMetadata[K]]
  def zoomLevel: Option[Int]

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

  def resample_to_power_of_two(
    col_power: Int,
    row_power: Int,
    resampleMethod: String
  ): TiledRasterLayer[K]

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

  def reproject(
    extent: java.util.Map[String, Double],
    layout: java.util.Map[String, Int],
    crs: String,
    resampleMethod: String
  ): TiledRasterLayer[K] = {
    val layoutDefinition = Right(LayoutDefinition(extent.toExtent, layout.toTileLayout))

    reproject(layoutDefinition, TileLayer.getCRS(crs).get, getReprojectOptions(resampleMethod))
  }

  def reproject(
    scheme: String,
    tileSize: Int,
    resolutionThreshold: Double,
    crs: String,
    resampleMethod: String
  ): TiledRasterLayer[K] = {
    val _crs = TileLayer.getCRS(crs).get

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
  ): TiledRasterLayer[K]

  def tileToLayout(
    extent: java.util.Map[String, Double],
    tileLayout: java.util.Map[String, Int],
    resampleMethod: String
  ): TiledRasterLayer[K] =
    tileToLayout(
      LayoutDefinition(extent.toExtent, tileLayout.toTileLayout),
      resampleMethod)

  protected def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: String
  ): TiledRasterLayer[K]

  def pyramid(
    startZoom: Int,
    endZoom: Int,
    resampleMethod: String
  ): Array[_] // Array[TiledRasterLayer[K]]

  def focal(
    operation: String,
    neighborhood: String,
    param1: Double,
    param2: Double,
    param3: Double
  ): TiledRasterLayer[K]

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

  def convertDataType(newType: String): TiledRasterLayer[_] =
    withRDD(rdd.convert(CellType.fromName(newType)))

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

  protected def withRDD(result: RDD[(K, MultibandTile)]): TiledRasterLayer[K]
}


class SpatialTiledRasterLayer(
  val zoomLevel: Option[Int],
  val rdd: RDD[(SpatialKey, MultibandTile)] with Metadata[TileLayerMetadata[SpatialKey]]
) extends TiledRasterLayer[SpatialKey] {

  def resample_to_power_of_two(
    col_power: Int,
    row_power: Int,
    resampleMethod: String
  ): TiledRasterLayer[SpatialKey] = {
    val method: ResampleMethod = TileLayer.getResampleMethod(resampleMethod)
    val cols = 1<<col_power
    val rows = 1<<row_power
    val rdd2 = rdd.mapValues({ tile => tile.resample(cols, rows, method) })

    val metadata = rdd.metadata
    val layout = LayoutDefinition(
      metadata.extent,
      TileLayout(
        metadata.layout.tileLayout.layoutCols,
        metadata.layout.tileLayout.layoutRows,
        cols,
        rows
      )
    )
    val metadata2 = metadata.copy(layout = layout)

    SpatialTiledRasterLayer(None, ContextRDD(rdd2, metadata2))
  }

  def lookup(
    col: Int,
    row: Int
  ): java.util.ArrayList[Array[Byte]] = {
    val tiles = rdd.lookup(SpatialKey(col, row))
    PythonTranslator.toPython[MultibandTile, ProtoMultibandTile](tiles)
  }

  def reproject(
    layout: Either[LayoutScheme, LayoutDefinition],
    crs: CRS,
    options: Reproject.Options
  ): TiledRasterLayer[SpatialKey] = {
    val (zoom, reprojected) = TileRDDReproject(rdd, crs, layout, options)
    SpatialTiledRasterLayer(Some(zoom), reprojected)
  }

  def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: String
  ): TiledRasterLayer[SpatialKey] = {
    val method: ResampleMethod = TileLayer.getResampleMethod(resampleMethod)
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

    SpatialTiledRasterLayer(None, tileLayer)
  }

  def pyramid(
    startZoom: Int,
    endZoom: Int,
    resampleMethod: String
  ): Array[TiledRasterLayer[SpatialKey]] = {
    require(! rdd.metadata.bounds.isEmpty, "Can not pyramid an empty RDD")

    val method: ResampleMethod = TileLayer.getResampleMethod(resampleMethod)
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

    leveledList.map{ x => SpatialTiledRasterLayer(Some(x._1), x._2) }.toArray
  }

  def focal(
    operation: String,
    neighborhood: String,
    param1: Double,
    param2: Double,
    param3: Double
  ): TiledRasterLayer[SpatialKey] = {
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

    SpatialTiledRasterLayer(None, multibandRDD)
  }

  def mask(geometries: Seq[MultiPolygon]): TiledRasterLayer[SpatialKey] = {
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
    SpatialTiledRasterLayer(zoomLevel, multiBand)
  }

  def stitch: Array[Byte] = {
    val contextRDD = ContextRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    PythonTranslator.toPython[Tile, ProtoTile](contextRDD.stitch.tile)
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
  ): TiledRasterLayer[SpatialKey] = {
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

    SpatialTiledRasterLayer(None, multibandRDD)
  }

  def hillshade(
    sc: SparkContext,
    azimuth: Double,
    altitude: Double,
    zFactor: Double,
    band: Int
  ): TiledRasterLayer[SpatialKey] = {
    val tileLayer = TileLayerRDD(rdd.mapValues(_.band(band)), rdd.metadata)

    implicit val _sc = sc

    val result = tileLayer.hillshade(azimuth, altitude, zFactor)

    val multibandRDD: MultibandTileLayerRDD[SpatialKey] =
      MultibandTileLayerRDD(result.mapValues{ tile => MultibandTile(tile) }, result.metadata)

    SpatialTiledRasterLayer(None, multibandRDD)
  }

  def reclassify(reclassifiedRDD: RDD[(SpatialKey, MultibandTile)]): TiledRasterLayer[SpatialKey] =
    SpatialTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def reclassifyDouble(reclassifiedRDD: RDD[(SpatialKey, MultibandTile)]): TiledRasterLayer[SpatialKey] =
    SpatialTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def withRDD(result: RDD[(SpatialKey, MultibandTile)]): TiledRasterLayer[SpatialKey] =
    SpatialTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(result, rdd.metadata))

  def toInt(converted: RDD[(SpatialKey, MultibandTile)]): TiledRasterLayer[SpatialKey] =
    SpatialTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toDouble(converted: RDD[(SpatialKey, MultibandTile)]): TiledRasterLayer[SpatialKey] =
    SpatialTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toProtoRDD(): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(SpatialKey, MultibandTile), ProtoTuple](rdd)

  def toPngRDD(pngRDD: RDD[(SpatialKey, Array[Byte])]): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(SpatialKey, Array[Byte]), ProtoTuple](pngRDD)

  def toGeoTiffRDD(
    tags: Tags,
    geotiffOptions: GeoTiffOptions
  ): JavaRDD[Array[Byte]] = {
    val mapTransform = MapKeyTransform(
      rdd.metadata.layout.extent,
      rdd.metadata.layout.layoutCols,
      rdd.metadata.layout.layoutRows)

    val crs = rdd.metadata.crs

    val geotiffRDD = rdd.map { x =>
      val transKey = ProjectedExtent(mapTransform(x._1), crs)

      (x._1, MultibandGeoTiff(x._2, transKey.extent, transKey.crs, tags, geotiffOptions).toByteArray)
    }

    PythonTranslator.toPython[(SpatialKey, Array[Byte]), ProtoTuple](geotiffRDD)
  }
}


class TemporalTiledRasterLayer(
  val zoomLevel: Option[Int],
  val rdd: RDD[(SpaceTimeKey, MultibandTile)] with Metadata[TileLayerMetadata[SpaceTimeKey]]
) extends TiledRasterLayer[SpaceTimeKey] {

  def resample_to_power_of_two(
    col_power: Int,
    row_power: Int,
    resampleMethod: String
  ): TiledRasterLayer[SpaceTimeKey] = {
    val method: ResampleMethod = TileLayer.getResampleMethod(resampleMethod)
    val cols = 1<<col_power
    val rows = 1<<row_power
    val rdd2 = rdd.mapValues({ tile => tile.resample(cols, rows, method) })

    val metadata = rdd.metadata
    val layout = LayoutDefinition(
      metadata.extent,
      TileLayout(
        metadata.layout.tileLayout.layoutCols,
        metadata.layout.tileLayout.layoutRows,
        cols,
        rows
      )
    )
    val metadata2 = metadata.copy(layout = layout)

    TemporalTiledRasterLayer(None, ContextRDD(rdd2, metadata2))
  }

  def mask(geometries: Seq[MultiPolygon]): TiledRasterLayer[SpaceTimeKey] = {
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
    TemporalTiledRasterLayer(zoomLevel, multiBand)
  }

  def reproject(
    layout: Either[LayoutScheme, LayoutDefinition],
    crs: CRS,
    options: Reproject.Options
  ): TiledRasterLayer[SpaceTimeKey] = {
    val (zoom, reprojected) = TileRDDReproject(rdd, crs, layout, options)
    TemporalTiledRasterLayer(Some(zoom), reprojected)
  }

  def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: String
  ): TiledRasterLayer[SpaceTimeKey] = {
    val method: ResampleMethod = TileLayer.getResampleMethod(resampleMethod)
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

    TemporalTiledRasterLayer(None, tileLayer)
  }

  def pyramid(
    startZoom: Int,
    endZoom: Int,
    resampleMethod: String
  ): Array[TiledRasterLayer[SpaceTimeKey]] = {
    require(! rdd.metadata.bounds.isEmpty, "Can not pyramid an empty RDD")

    val method: ResampleMethod = TileLayer.getResampleMethod(resampleMethod)
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

    leveledList.map{ x => TemporalTiledRasterLayer(Some(x._1), x._2) }.toArray
  }

  def focal(
    operation: String,
    neighborhood: String,
    param1: Double,
    param2: Double,
    param3: Double
  ): TiledRasterLayer[SpaceTimeKey] = {
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

    TemporalTiledRasterLayer(None, multibandRDD)
  }

  def costDistance(
    sc: SparkContext,
    geometries: Seq[Geometry],
    maxDistance: Double
  ): TiledRasterLayer[SpaceTimeKey] = {
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

    TemporalTiledRasterLayer(None, multibandRDD)
  }

  def hillshade(
    sc: SparkContext,
    azimuth: Double,
    altitude: Double,
    zFactor: Double,
    band: Int
  ): TiledRasterLayer[SpaceTimeKey] = {
    val tileLayer = TileLayerRDD(rdd.mapValues(_.band(band)), rdd.metadata)

    implicit val _sc = sc

    val result = tileLayer.hillshade(azimuth, altitude, zFactor)

    val multibandRDD: MultibandTileLayerRDD[SpaceTimeKey] =
      MultibandTileLayerRDD(result.mapValues(MultibandTile(_)), result.metadata)

    TemporalTiledRasterLayer(None, multibandRDD)
  }

  def reclassify(reclassifiedRDD: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterLayer[SpaceTimeKey] =
    TemporalTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def reclassifyDouble(reclassifiedRDD: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterLayer[SpaceTimeKey] =
    TemporalTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def withRDD(result: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterLayer[SpaceTimeKey] =
    TemporalTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(result, rdd.metadata))

  def toInt(converted: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterLayer[SpaceTimeKey] =
    TemporalTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toDouble(converted: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterLayer[SpaceTimeKey] =
    TemporalTiledRasterLayer(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toProtoRDD(): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(SpaceTimeKey, MultibandTile), ProtoTuple](rdd)

  def toPngRDD(pngRDD: RDD[(SpaceTimeKey, Array[Byte])]): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(SpaceTimeKey, Array[Byte]), ProtoTuple](pngRDD)

  def toGeoTiffRDD(
    tags: Tags,
    geotiffOptions: GeoTiffOptions
  ): JavaRDD[Array[Byte]] = {
    val mapTransform = MapKeyTransform(
      rdd.metadata.layout.extent,
      rdd.metadata.layout.layoutCols,
      rdd.metadata.layout.layoutRows)

    val crs = rdd.metadata.crs

    val geotiffRDD = rdd.map { x =>
      val transKey = TemporalProjectedExtent(mapTransform(x._1), crs, x._1.instant)

      (x._1, MultibandGeoTiff(x._2, transKey.extent, transKey.crs, tags, geotiffOptions).toByteArray)
    }

    PythonTranslator.toPython[(SpaceTimeKey, Array[Byte]), ProtoTuple](geotiffRDD)
  }
}


object SpatialTiledRasterLayer {
  def fromProtoEncodedRDD(
    javaRDD: JavaRDD[Array[Byte]],
    metadata: String
  ): SpatialTiledRasterLayer = {
    val md = metadata.parseJson.convertTo[TileLayerMetadata[SpatialKey]]
    val tileLayer = MultibandTileLayerRDD(
      PythonTranslator.fromPython[(SpatialKey, MultibandTile), ProtoTuple](javaRDD, ProtoTuple.parseFrom), md)

    SpatialTiledRasterLayer(None, tileLayer)
  }

  def apply(
    zoomLevel: Option[Int],
    rdd: RDD[(SpatialKey, MultibandTile)] with Metadata[TileLayerMetadata[SpatialKey]]
  ): SpatialTiledRasterLayer =
    new SpatialTiledRasterLayer(zoomLevel, rdd)

  def rasterizeGeometry(sc: SparkContext, geomWKB: ArrayList[Array[Byte]], geomCRSStr: String,
    requestedZoom: Int, fillValue: Double, cellTypeString: String, options: Rasterizer.Options,
    numPartitions: Integer
  ): TiledRasterLayer[SpatialKey]= {
    val cellType = CellType.fromName(cellTypeString)
    val geoms = geomWKB.asScala.map(WKB.read)
    val srcCRS = TileLayer.getCRS(geomCRSStr).get
    val LayoutLevel(z, ld) = ZoomedLayoutScheme(srcCRS).levelForZoom(requestedZoom)
    val maptrans = ld.mapTransform
    val fullEnvelope = geoms.map(_.envelope).reduce(_ combine _)
    val gb @ GridBounds(cmin, rmin, cmax, rmax) = maptrans(fullEnvelope)

    val geomsRdd = sc.parallelize(geoms)
    import geotrellis.raster.rasterize.Rasterizer.Options
    val tiles = RasterizeRDD.fromGeometry(
      geoms = geomsRdd,
      layout = ld,
      ct = cellType,
      value = fillValue,
      options = Option(options).getOrElse(Options.DEFAULT),
      numPartitions = Option(numPartitions).map(_.toInt).getOrElse(math.max(gb.size / 512, 1)))
    val metadata = TileLayerMetadata(cellType, ld, maptrans(gb), srcCRS, KeyBounds(gb))
    SpatialTiledRasterLayer(Some(requestedZoom),
      MultibandTileLayerRDD(tiles.mapValues(MultibandTile(_)), metadata))
  }

  def euclideanDistance(sc: SparkContext, geomWKB: Array[Byte], geomCRSStr: String, cellTypeString: String, requestedZoom: Int): TiledRasterLayer[SpatialKey]= {
    val cellType = CellType.fromName(cellTypeString)
    val geom = WKB.read(geomWKB)
    val srcCRS = TileLayer.getCRS(geomCRSStr).get
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

    SpatialTiledRasterLayer(Some(z), MultibandTileLayerRDD(mbtileRDD, metadata))
  }
}


object TemporalTiledRasterLayer {
  def fromProtoEncodedRDD(
    javaRDD: JavaRDD[Array[Byte]],
    metadata: String
  ): TemporalTiledRasterLayer = {
    val md = metadata.parseJson.convertTo[TileLayerMetadata[SpaceTimeKey]]
    val tileLayer = MultibandTileLayerRDD(
      PythonTranslator.fromPython[(SpaceTimeKey, MultibandTile), ProtoTuple](javaRDD, ProtoTuple.parseFrom), md)

    TemporalTiledRasterLayer(None, tileLayer)
  }

  def apply(
    zoomLevel: Option[Int],
    rdd: RDD[(SpaceTimeKey, MultibandTile)] with Metadata[TileLayerMetadata[SpaceTimeKey]]
  ): TemporalTiledRasterLayer =
    new TemporalTiledRasterLayer(zoomLevel, rdd)

  def rasterize(
    sc: SparkContext,
    geometryBytes: Array[Byte],
    extent: java.util.Map[String, Double],
    crs: String,
    instant: Int,
    cols: Int,
    rows: Int,
    fillValue: Int
  ): TiledRasterLayer[SpaceTimeKey] = {
    val rasterExtent = RasterExtent(extent.toExtent, cols, rows)
    val temporalExtent =
      TemporalProjectedExtent(rasterExtent.extent, TileLayer.getCRS(crs).get, instant.toInt)

    val tile = Rasterizer.rasterizeWithValue(WKB.read(geometryBytes), rasterExtent, fillValue)
    val rdd = sc.parallelize(Array((temporalExtent, MultibandTile(tile))))
    val tileLayout = TileLayout(1, 1, cols, rows)
    val layoutDefinition = LayoutDefinition(rasterExtent.extent, tileLayout)

    val metadata = rdd.collectMetadata[SpaceTimeKey](layoutDefinition)

    TemporalTiledRasterLayer(None, MultibandTileLayerRDD(rdd.tileToLayout(metadata), metadata))
  }
}
