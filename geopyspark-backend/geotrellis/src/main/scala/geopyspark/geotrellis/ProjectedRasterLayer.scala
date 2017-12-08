package geopyspark.geotrellis

import geopyspark.util._
import GeoTrellisUtils._

import geotrellis.proj4._
import geotrellis.raster._
import geotrellis.raster.io.geotiff.{GeoTiffOptions, MultibandGeoTiff, Tags}
import geotrellis.raster.resample.ResampleMethod
import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.spark.reproject._
import geotrellis.spark.tiling._
import geotrellis.vector._

import org.apache.spark.api.java.JavaRDD
import org.apache.spark._
import org.apache.spark.rdd._

import protos.tupleMessages.ProtoTuple
import protos.extentMessages.ProtoProjectedExtent

import scala.util.{Either, Left, Right}
import scala.collection.JavaConverters._

import java.util.ArrayList

import spray.json._


class ProjectedRasterLayer(val rdd: RDD[(ProjectedExtent, MultibandTile)]) extends RasterLayer[ProjectedExtent] {

  def collectMetadata(layoutType: LayoutType): String = {
    val sms = RasterSummary.collect[ProjectedExtent, SpatialKey](rdd)
    require(sms.length == 1, s"Multiple raster CRS layers found: ${sms.map(_.crs).toList}")

    sms.head.toTileLayerMetadata(layoutType)._1.toJson.compactPrint
  }

  def collectMetadata(layoutDefinition: LayoutDefinition): String = {
    val sms = RasterSummary.collect[ProjectedExtent, SpatialKey](rdd)
    require(sms.length == 1, s"Multiple raster CRS layers found: ${sms.map(_.crs).toList}")
    val sm = sms.head

    TileLayerMetadata[SpatialKey](
      sm.cellType,
      layoutDefinition,
      sm.extent,
      sm.crs,
      sm.bounds.setSpatialBounds(layoutDefinition.mapTransform(sm.extent))
    ).toJson.compactPrint
  }

  def tileToLayout(tileLayerMetadata: String, resampleMethod: ResampleMethod): TiledRasterLayer[SpatialKey] = {
    val md = tileLayerMetadata.parseJson.convertTo[TileLayerMetadata[SpatialKey]]
    new SpatialTiledRasterLayer(None, MultibandTileLayerRDD(rdd.tileToLayout(md, resampleMethod), md))
  }

  def tileToLayout(layoutDefinition: LayoutDefinition, resampleMethod: ResampleMethod): TiledRasterLayer[SpatialKey] = {
    val sms = RasterSummary.collect[ProjectedExtent, SpatialKey](rdd)
    require(sms.length == 1, s"Multiple raster CRS layers found: ${sms.map(_.crs).toList}")
    val sm = sms.head

    val metadata = TileLayerMetadata[SpatialKey](
      sm.cellType,
      layoutDefinition,
      sm.extent,
      sm.crs,
      sm.bounds.setSpatialBounds(layoutDefinition.mapTransform(sm.extent))
    )

    SpatialTiledRasterLayer(None, MultibandTileLayerRDD(rdd.tileToLayout(metadata, resampleMethod), metadata))
  }

  def tileToLayout(layoutType: LayoutType, resampleMethod: ResampleMethod): TiledRasterLayer[SpatialKey] = {
    val sms = RasterSummary.collect[ProjectedExtent, SpatialKey](rdd)
    require(sms.length == 1, s"Multiple raster CRS layers found: ${sms.map(_.crs).toList}")
    val sm = sms.head
    val (metadata, zoom) = sm.toTileLayerMetadata(layoutType)
    val tiled = rdd.tileToLayout(metadata, resampleMethod)
    new SpatialTiledRasterLayer(zoom, MultibandTileLayerRDD(tiled, metadata))
  }

  def reproject(targetCRS: String, resampleMethod: ResampleMethod): ProjectedRasterLayer = {
    val crs = TileLayer.getCRS(targetCRS).get
    new ProjectedRasterLayer(rdd.reproject(crs, resampleMethod))
  }

  def reproject(targetCRS: String, layoutType: LayoutType, resampleMethod: ResampleMethod): TiledRasterLayer[SpatialKey] = {
    val crs = TileLayer.getCRS(targetCRS).get
    val tiled = tileToLayout(LocalLayout(256), resampleMethod).rdd
    layoutType match {
      case GlobalLayout(tileSize, null, threshold) =>
        val scheme = new ZoomedLayoutScheme(crs, tileSize, threshold)
        val (zoom, reprojected) = tiled.reproject(crs, scheme, resampleMethod)
        new SpatialTiledRasterLayer(Some(zoom), reprojected)

      case GlobalLayout(tileSize, zoom, threshold) =>
        val scheme = new ZoomedLayoutScheme(crs, tileSize, threshold)
        val (_, reprojected) = tiled.reproject(crs, scheme.levelForZoom(zoom).layout, resampleMethod)
        new SpatialTiledRasterLayer(Some(zoom), reprojected)

      case LocalLayout(tileCols, tileRows) =>
        val (_, reprojected) = tiled.reproject(crs, FloatingLayoutScheme(tileCols, tileRows), resampleMethod)
        new SpatialTiledRasterLayer(None, reprojected)
    }
  }

  def reproject(
    target_crs: String,
    layoutDefinition: LayoutDefinition,
    resampleMethod: ResampleMethod
  ): TiledRasterLayer[SpatialKey] = {
    val tiled = tileToLayout(layoutDefinition, resampleMethod).rdd
    val (zoom, reprojected) = TileRDDReproject(tiled, TileLayer.getCRS(target_crs).get, Right(layoutDefinition), resampleMethod)
    SpatialTiledRasterLayer(Some(zoom), reprojected)
  }

  def reclassify(reclassifiedRDD: RDD[(ProjectedExtent, MultibandTile)]): RasterLayer[ProjectedExtent] =
    ProjectedRasterLayer(reclassifiedRDD)

  def reclassifyDouble(reclassifiedRDD: RDD[(ProjectedExtent, MultibandTile)]): RasterLayer[ProjectedExtent] =
    ProjectedRasterLayer(reclassifiedRDD)

  def withRDD(result: RDD[(ProjectedExtent, MultibandTile)]): RasterLayer[ProjectedExtent] =
    ProjectedRasterLayer(result)

  def toProtoRDD(): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(ProjectedExtent, MultibandTile), ProtoTuple](rdd)

  def toPngRDD(pngRDD: RDD[(ProjectedExtent, Array[Byte])]): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(ProjectedExtent, Array[Byte]), ProtoTuple](pngRDD)

  def toGeoTiffRDD(
    tags: Tags,
    geotiffOptions: GeoTiffOptions
  ): JavaRDD[Array[Byte]] = {
    val geotiffRDD = rdd.map { x =>
      (x._1, MultibandGeoTiff(x._2, x._1.extent, x._1.crs, tags, geotiffOptions).toByteArray)
    }

    PythonTranslator.toPython[(ProjectedExtent, Array[Byte]), ProtoTuple](geotiffRDD)
  }

  def collectKeys(): java.util.ArrayList[Array[Byte]] =
    PythonTranslator.toPython[ProjectedExtent, ProtoProjectedExtent](rdd.keys.collect)
}


object ProjectedRasterLayer {
  def fromProtoEncodedRDD(javaRDD: JavaRDD[Array[Byte]]): ProjectedRasterLayer =
    ProjectedRasterLayer(
      PythonTranslator.fromPython[
        (ProjectedExtent, MultibandTile), ProtoTuple
      ](javaRDD, ProtoTuple.parseFrom))

  def apply(rdd: RDD[(ProjectedExtent, MultibandTile)]): ProjectedRasterLayer =
    new ProjectedRasterLayer(rdd)

  def unionLayers(
    sc: SparkContext,
    layers: ArrayList[ProjectedRasterLayer]
  ): ProjectedRasterLayer =
    ProjectedRasterLayer(sc.union(layers.asScala.map(_.rdd)))

  def combineBands(sc: SparkContext, layers: ArrayList[ProjectedRasterLayer]): ProjectedRasterLayer =
    ProjectedRasterLayer(TileLayer.combineBands[ProjectedExtent, ProjectedRasterLayer](sc, layers))
}
