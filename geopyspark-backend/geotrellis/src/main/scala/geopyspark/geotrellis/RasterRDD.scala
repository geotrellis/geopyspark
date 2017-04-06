package geopyspark.geotrellis

import geotrellis.util._
import geotrellis.proj4._
import geotrellis.vector._
import geotrellis.vector.io._
import geotrellis.raster._
import geotrellis.raster.io._
import geotrellis.raster.merge._
import geotrellis.raster.prototype._
import geotrellis.raster.resample._
import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.spark.io.json._
import geotrellis.spark.io.avro._
import geotrellis.spark.tiling._

import spray.json._
import spray.json.DefaultJsonProtocol._

import org.apache.spark._
import org.apache.spark.rdd._
import org.apache.spark.api.java.JavaRDD

import scala.reflect._
import scala.util._
import scala.collection.JavaConverters._

import collection.JavaConversions._

import java.util.Map


object TileRDD {
  def getResampleMethod(resampleMethod: String): ResampleMethod =
    resampleMethod match {
      case "NearestNeighbor" => NearestNeighbor
      case "Bilinear" => Bilinear
      case "CubicConvolution" => CubicConvolution
      case "CubicSpline" => CubicSpline
      case "Lanczos" => Lanczos
      case "Average" => Average
      case "Mode" => Mode
      case "Median" => Median
      case "Max" => Max
      case "Min" => Min
      case _ => throw new Exception(s"$resampleMethod, is not a known sampling method")
    }

  def getCRS(crs: String): Option[CRS] = {
    Try(CRS.fromName(crs))
      .recover({ case e => CRS.fromString(crs) })
      .recover({ case e => CRS.fromEpsgCode(crs.toInt) })
      .toOption
  }
}

abstract class TileRDD[K: ClassTag] {
  def rdd: RDD[(K, MultibandTile)]
  def keyClass: Class[_] = classTag[K].runtimeClass
  def keyClassName: String = keyClass.getName
}

/**
 * RDD of Rasters, untiled and unsorted
 */
abstract class RasterRDD[K: AvroRecordCodec: ClassTag] extends TileRDD[K] {
  def rdd: RDD[(K, MultibandTile)]

  /** Encode RDD as Avro bytes and return it with avro schema used */
  def toAvroRDD(): (JavaRDD[Array[Byte]], String) = PythonTranslator.toPython(rdd)

  // TODO: get rid of this overload, just use the String interface
  protected def collectMetadata(crs: Option[CRS], extent: Option[Extent], layout: Option[TileLayout], tileSize: Int): String

  def collect_metadata(crs: String, extent: String, layout: String, tileSize: Int): String =
    collectMetadata(
      crs = Option(crs).flatMap(TileRDD.getCRS),
      extent = Option(extent).flatMap(_.parseJson.convertTo[Option[Extent]]),
      layout = Option(layout).flatMap(_.parseJson.convertTo[Option[TileLayout]]),
      tileSize = tileSize
    )

  def cutTiles(layerMetadata: String, resampleMethod: String): TiledRasterRDD[_]

  def tileToLayout(tileLayerMetadata: String, resampleMethod: String): TiledRasterRDD[_]

  def reproject(target_crs: String, resampleMethod: String): RasterRDD[_]
}

class ProjectedRasterRDD(val rdd: RDD[(ProjectedExtent, MultibandTile)]) extends RasterRDD[ProjectedExtent] {

  def collectMetadata(crs: Option[CRS], extent: Option[Extent], layout: Option[TileLayout], tileSize: Int): String = {
      (crs, extent, layout) match {
        case (Some(crs), Some(extent), Some(layout)) =>
          rdd.collectMetadata[SpatialKey](crs, LayoutDefinition(extent, layout))
        case (None, Some(extent), Some(layout)) =>
          rdd.collectMetadata[SpatialKey](LayoutDefinition(extent, layout))
        case (Some(crs), _, _) =>
          rdd.collectMetadata[SpatialKey](crs, FloatingLayoutScheme(tileSize, tileSize))._2
        case (None, None, None) =>
          rdd.collectMetadata[SpatialKey](FloatingLayoutScheme(tileSize, tileSize))._2
        case _ =>
          throw new IllegalArgumentException(s"Can't handle $crs, $extent, $layout, $tileSize")
      }
  }.toJson.compactPrint

  def cutTiles(layerMetadata: String, resampleMethod: String): TiledRasterRDD[SpatialKey] = {
    val md = layerMetadata.parseJson.convertTo[TileLayerMetadata[SpatialKey]]
    val rm = TileRDD.getResampleMethod(resampleMethod)
    new SpatialTiledRasterRDD(None, MultibandTileLayerRDD(rdd.cutTiles(md, rm), md))
  }

  def tileToLayout(tileLayerMetadata: String, resampleMethod: String): TiledRasterRDD[SpatialKey] = {
    val md = tileLayerMetadata.parseJson.convertTo[TileLayerMetadata[SpatialKey]]
    val rm = TileRDD.getResampleMethod(resampleMethod)
    new SpatialTiledRasterRDD(None, MultibandTileLayerRDD(rdd.tileToLayout(md, rm), md))
  }

  def reproject(target_crs: String, resampleMethod: String): ProjectedRasterRDD = {
    val tcrs = TileRDD.getCRS(target_crs).get
    val resample = TileRDD.getResampleMethod(resampleMethod)
    new ProjectedRasterRDD(rdd.reproject(tcrs, resample))
  }

}

class TemporalRasterRDD(val rdd: RDD[(TemporalProjectedExtent, MultibandTile)]) extends RasterRDD[TemporalProjectedExtent] {

  def collectMetadata(crs: Option[CRS], extent: Option[Extent], layout: Option[TileLayout], tileSize: Int): String = {
      (crs, extent, layout) match {
        case (Some(crs), Some(extent), Some(layout)) =>
          rdd.collectMetadata[SpaceTimeKey](crs, LayoutDefinition(extent, layout))
        case (None, Some(extent), Some(layout)) =>
          rdd.collectMetadata[SpaceTimeKey](LayoutDefinition(extent, layout))
        case (Some(crs), _, _) =>
          rdd.collectMetadata[SpaceTimeKey](crs, FloatingLayoutScheme(tileSize, tileSize))._2
        case (None, None, None) =>
          rdd.collectMetadata[SpaceTimeKey](FloatingLayoutScheme())._2
        case _ =>
          throw new IllegalArgumentException(s"Can't handle $crs, $extent, $layout, $tileSize")
      }
  }.toJson.compactPrint

  def cutTiles(layerMetadata: String, resampleMethod: String): TiledRasterRDD[SpaceTimeKey] = {
    val md = layerMetadata.parseJson.convertTo[TileLayerMetadata[SpaceTimeKey]]
    val rm = TileRDD.getResampleMethod(resampleMethod)
    val tiles = rdd.cutTiles[SpaceTimeKey](md, rm)
    new TemporalTiledRasterRDD(None, MultibandTileLayerRDD(tiles, md))
  }

  def tileToLayout(layerMetadata: String, resampleMethod: String): TiledRasterRDD[SpaceTimeKey] = {
    val md = layerMetadata.parseJson.convertTo[TileLayerMetadata[SpaceTimeKey]]
    val rm = TileRDD.getResampleMethod(resampleMethod)
    new TemporalTiledRasterRDD(None, MultibandTileLayerRDD(rdd.tileToLayout(md, rm), md))
  }

  def reproject(target_crs: String, resampleMethod: String): TemporalRasterRDD = {
    val tcrs = TileRDD.getCRS(target_crs).get
    val resample = TileRDD.getResampleMethod(resampleMethod)
    new TemporalRasterRDD(rdd.reproject(tcrs, resample))
  }
}
