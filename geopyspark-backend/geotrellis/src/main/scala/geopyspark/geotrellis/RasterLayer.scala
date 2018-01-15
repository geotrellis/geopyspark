package geopyspark.geotrellis

import geopyspark.geotrellis.GeoTrellisUtils._

import geotrellis.util._
import geotrellis.proj4._
import geotrellis.vector._
import geotrellis.vector.io._
import geotrellis.vector.io.wkt.WKT
import geotrellis.raster._
import geotrellis.raster.resample._
import geotrellis.raster.render._
import geotrellis.raster.histogram.Histogram
import geotrellis.raster.io.geotiff._
import geotrellis.raster.io.geotiff.compression._
import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.spark.io.json._
import geotrellis.spark.tiling._

import spray.json._
import spray.json.DefaultJsonProtocol._

import spire.syntax.order._
import spire.std.any._

import org.apache.spark._
import org.apache.spark.rdd._
import org.apache.spark.api.java.JavaRDD
import org.apache.spark.storage.StorageLevel

import scala.reflect._
import scala.util._
import scala.collection.JavaConverters._
import scala.collection.immutable.HashMap


/**
 * RDD of Rasters, untiled and unsorted
 */
abstract class RasterLayer[K](implicit ev0: ClassTag[K], ev1: Component[K, ProjectedExtent]) extends TileLayer[K] with Serializable {
  def rdd: RDD[(K, MultibandTile)]

  def toProtoRDD(): JavaRDD[Array[Byte]]

  def collectKeys(): java.util.ArrayList[Array[Byte]]

  def bands(band: Int): RasterLayer[K] =
    withRDD(rdd.mapValues { multibandTile => multibandTile.subsetBands(band) })

  def bands(bands: java.util.ArrayList[Int]): RasterLayer[K] =
    withRDD(rdd.mapValues { multibandTile => multibandTile.subsetBands(bands.asScala) })

  def collectMetadata(layoutType: LayoutType): String
  def collectMetadata(layoutDefinition: LayoutDefinition): String

  def convertDataType(newType: String): RasterLayer[_] =
    withRDD(rdd.map { x => (x._1, x._2.convert(CellType.fromName(newType))) })

  protected def tileToLayout(tileLayerMetadata: String, resampleMethod: ResampleMethod): TiledRasterLayer[_]
  def tileToLayout(layoutType: LayoutType, resampleMethod: ResampleMethod): TiledRasterLayer[_]
  protected def tileToLayout(layoutDefinition: LayoutDefinition, resampleMethod: ResampleMethod): TiledRasterLayer[_]

  protected def reproject(targetCRS: String, resampleMethod: ResampleMethod): RasterLayer[K]
  protected def reproject(targetCRS: String, layoutType: LayoutType, resampleMethod: ResampleMethod): TiledRasterLayer[_]
  protected def reproject(targetCRS: String, layoutDefinition: LayoutDefinition, resampleMethod: ResampleMethod): TiledRasterLayer[_]
  protected def withRDD(result: RDD[(K, MultibandTile)]): RasterLayer[K]

  def merge(partitioner: Partitioner): RasterLayer[K] =
    partitioner match {
      case p: Partitioner => withRDD(rdd.merge(Some(p)))
      case null => withRDD(rdd.merge())
    }
}
