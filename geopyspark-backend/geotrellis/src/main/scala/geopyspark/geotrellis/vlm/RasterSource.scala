package geopyspark.geotrellis.vlm

import geopyspark.geotrellis.{PartitionStrategy, ProjectedRasterLayer, SpatialTiledRasterLayer}
import geopyspark.geotrellis.{LayoutType => GPSLayoutType, LocalLayout => GPSLocalLayout, GlobalLayout => GPSGlobalLayout}

import geopyspark.geotrellis.Constants.{GEOTRELLIS, GDAL}

import geotrellis.contrib.vlm._
import geotrellis.contrib.vlm.gdal.GDALRasterSource

import geotrellis.raster._
import geotrellis.raster.resample._
import geotrellis.spark._
import geotrellis.spark.tiling._
import geotrellis.proj4._
import geotrellis.vector._
import geotrellis.util._

import org.apache.spark.SparkContext
import org.apache.spark.rdd.RDD

import scala.collection.JavaConverters._


object RasterSource {
  def read(
    sc: SparkContext,
    layerType: String,
    paths: java.util.ArrayList[String],
    targetCRS: String,
    resampleMethod: ResampleMethod,
    partitionStrategy: PartitionStrategy,
    readMethod: String
  ): ProjectedRasterLayer =
    read(
      sc,
      layerType,
      sc.parallelize(paths.asScala, paths.size),
      targetCRS,
      resampleMethod,
      partitionStrategy,
      readMethod
    )

  def read(
    sc: SparkContext,
    layerType: String,
    rdd: RDD[String],
    targetCRS: String,
    resampleMethod: ResampleMethod,
    partitionStrategy: PartitionStrategy,
    readMethod: String
  ): ProjectedRasterLayer = {
    val rasterSourceRDD: RDD[RasterSource] =
      (readMethod match {
        case GEOTRELLIS => rdd.map { new GeoTiffRasterSource(_): RasterSource }
        case GDAL => rdd.map { GDALRasterSource(_): RasterSource }
      }).cache()

    val reprojectedSourcesRDD: RDD[RasterSource] =
      targetCRS match {
        case crs: String =>
          rasterSourceRDD.map { _.reproject(CRS.fromString(crs), resampleMethod) }
        case null =>
          rasterSourceRDD
      }

    val projectedRasterRDD: RDD[(ProjectedExtent, MultibandTile)] =
      reprojectedSourcesRDD.flatMap { source: RasterSource =>
        source.read(source.extent) match {
          case Some(raster) => Some((ProjectedExtent(raster.extent, source.crs), raster.tile))
          case None => None
        }
      }

    rasterSourceRDD.unpersist()

    ProjectedRasterLayer(projectedRasterRDD)
  }

  def readToLayout(
    sc: SparkContext,
    layerType: String,
    paths: java.util.ArrayList[String],
    layoutType: GPSLayoutType,
    targetCRS: String,
    resampleMethod: ResampleMethod,
    partitionStrategy: PartitionStrategy,
    readMethod: String
  ): SpatialTiledRasterLayer =
    readToLayout(
      sc,
      layerType,
      sc.parallelize(paths.asScala, paths.size),
      layoutType,
      targetCRS,
      resampleMethod,
      partitionStrategy,
      readMethod
    )

  def readToLayout(
    sc: SparkContext,
    layerType: String,
    rdd: RDD[String],
    layoutType: LayoutType,
    targetCRS: String,
    resampleMethod: ResampleMethod,
    partitionStrategy: PartitionStrategy,
    readMethod: String
  ): SpatialTiledRasterLayer = {
    // TODO: These are the things that still need to be done:
    // 1. Support TemporalTiledRasterLayer (ie. generic K)
    // 2. Use the partitionStrategy parameter

    val rasterSourceRDD: RDD[RasterSource] =
      (readMethod match {
        case GEOTRELLIS => rdd.map { new GeoTiffRasterSource(_): RasterSource }
        case GDAL => rdd.map { GDALRasterSource(_): RasterSource }
      }).cache()

    val reprojectedSourcesRDD: RDD[RasterSource] =
      targetCRS match {
        case crs: String =>
          rasterSourceRDD.map { _.reproject(CRS.fromString(crs), resampleMethod) }
        case null =>
          rasterSourceRDD
      }

    val metadata: RasterSummary = RasterSummary.fromRDD(reprojectedSourcesRDD)

    val LayoutLevel(zoom, layout) =
      layoutType match {
        case global: GlobalLayout =>
          val scheme = ZoomedLayoutScheme(metadata.crs, global.tileSize)
          scheme.levelForZoom(global.zoom)
        case local: LocalLayout =>
          val scheme = FloatingLayoutScheme(local.tileCols, local.tileRows)
          metadata.levelFor(scheme)
      }

    val layoutRDD: RDD[LayoutTileSource] = reprojectedSourcesRDD.map { _.tileToLayout(layout, resampleMethod) }

    val collectedMetadata: RasterSummary = RasterSummary.fromRDD(layoutRDD.map { _.source })

    val tileLayerMetadata: TileLayerMetadata[SpatialKey] =
      collectedMetadata.toTileLayerMetadata(layout, zoom)._1

    val tiledRDD: RDD[(SpatialKey, MultibandTile)] =
      layoutRDD.flatMap { case source =>
        source.keys.toIterator.flatMap { key: SpatialKey =>
          source.rasterRef(key).raster match {
            case Some(raster) => Some((key, raster.tile))
            case None => None
          }
        }
      }

    rasterSourceRDD.unpersist()

    val contextRDD: MultibandTileLayerRDD[SpatialKey] =
      ContextRDD(tiledRDD, tileLayerMetadata)

    SpatialTiledRasterLayer(zoom, contextRDD)
  }

  implicit def gps2VLM(layoutType: GPSLayoutType): LayoutType =
    layoutType match {
      case local: GPSLocalLayout => LocalLayout(local.tileCols, local.tileRows)
      case global: GPSGlobalLayout => GlobalLayout(global.tileSize, global.zoom, global.threshold)
    }
}