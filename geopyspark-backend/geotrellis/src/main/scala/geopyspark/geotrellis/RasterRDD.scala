package geopyspark.geotrellis

import geopyspark.geotrellis.GeoTrellisUtils._

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

  def collectMetadata(
    extent: java.util.Map[String, Double],
    layout: java.util.Map[String, Int],
    crs: String
  ): String = {
    val layoutDefinition = Right(LayoutDefinition(extent.toExtent, layout.toTileLayout))

    collectMetadata(layoutDefinition, crs)
  }

  def collectMetadata(tileSize: String, crs: String): String = {
    val layoutScheme =
      if (tileSize != "")
        Left(FloatingLayoutScheme(tileSize.toInt))
      else
        Left(FloatingLayoutScheme())

    collectMetadata(layoutScheme, crs)
  }

  def collectMetadata(layout: Either[LayoutScheme, LayoutDefinition], crs: String): String

  def cutTiles(layerMetadata: String, resampleMethod: String): TiledRasterRDD[_]

  def tileToLayout(tileLayerMetadata: String, resampleMethod: String): TiledRasterRDD[_]

  def reproject(target_crs: String, resampleMethod: String): RasterRDD[_]
}

class ProjectedRasterRDD(val rdd: RDD[(ProjectedExtent, MultibandTile)]) extends RasterRDD[ProjectedExtent] {

  def collectMetadata(layout: Either[LayoutScheme, LayoutDefinition], crs: String): String = {
    (TileRDD.getCRS(crs), layout) match {
      case (Some(crs), Right(layoutDefinition)) =>
          rdd.collectMetadata[SpatialKey](crs, layoutDefinition)
      case (None, Right(layoutDefinition)) =>
          rdd.collectMetadata[SpatialKey](layoutDefinition)
      case (Some(crs), Left(layoutScheme)) =>
          rdd.collectMetadata[SpatialKey](crs, layoutScheme)._2
      case (None, Left(layoutScheme)) =>
          rdd.collectMetadata[SpatialKey](layoutScheme)._2
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

  def collectMetadata(layout: Either[LayoutScheme, LayoutDefinition], crs: String): String = {
    (TileRDD.getCRS(crs), layout) match {
      case (Some(crs), Right(layoutDefinition)) =>
          rdd.collectMetadata[SpaceTimeKey](crs, layoutDefinition)
      case (None, Right(layoutDefinition)) =>
          rdd.collectMetadata[SpaceTimeKey](layoutDefinition)
      case (Some(crs), Left(layoutScheme)) =>
          rdd.collectMetadata[SpaceTimeKey](crs, layoutScheme)._2
      case (None, Left(layoutScheme)) =>
          rdd.collectMetadata[SpaceTimeKey](layoutScheme)._2
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

object ProjectedRasterRDD {
  def apply(javaRDD: JavaRDD[Array[Byte]], schema: String): ProjectedRasterRDD =
    ProjectedRasterRDD(PythonTranslator.fromPython(javaRDD, Some(schema)))

  def apply(rdd: RDD[(ProjectedExtent, MultibandTile)]): ProjectedRasterRDD =
    new ProjectedRasterRDD(rdd)
}

object TemporalRasterRDD {
  def apply(javaRDD: JavaRDD[Array[Byte]], schema: String): TemporalRasterRDD =
    TemporalRasterRDD(PythonTranslator.fromPython(javaRDD, Some(schema)))

  def apply(rdd: RDD[(TemporalProjectedExtent, MultibandTile)]): TemporalRasterRDD =
    new TemporalRasterRDD(rdd)
}
