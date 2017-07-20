package geopyspark.geotrellis.io

import geopyspark.geotrellis._

import geotrellis.vector._
import geotrellis.vector.io.wkt.WKT
import geotrellis.vector.io.wkb.WKB
import geotrellis.raster._
import geotrellis.proj4._
import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.spark.io.accumulo._
import geotrellis.spark.io.cassandra._
import geotrellis.spark.io.file._
import geotrellis.spark.io.hadoop._
import geotrellis.spark.io.hbase._
import geotrellis.spark.io.json._
import geotrellis.spark.io.s3._

import org.apache.spark._
import org.apache.spark.api.java.JavaRDD
import org.apache.spark.rdd.RDD

import spray.json._

import java.time.ZonedDateTime
import java.util.ArrayList
import scala.collection.JavaConverters._
import scala.collection.mutable

import geopyspark.geotrellis.PythonTranslator


/**
  * General interface for reading.
  */
abstract class LayerReaderWrapper {
  def read(
    keyType: String,
    layerName: String,
    zoom: Int,
    numPartitions: Int
  ): TiledRasterLayer[_]

  def query(
    keyType: String,
    layerName: String,
    zoom: Int,
    queryGeometryBytes: Array[Byte],
    queryIntervalStrings: ArrayList[String],
    projQuery: String,
    numPartitions: Int
  ): TiledRasterLayer[_]
}


/**
  * Base wrapper class for all backends that provide a
  * FilteringLayerReader[LayerId].
  */
abstract class FilteringLayerReaderWrapper()
    extends LayerReaderWrapper {

  def attributeStore: AttributeStore
  def layerReader: FilteringLayerReader[LayerId]

  def layerIds: Array[java.util.Map[String, Any]] =
    attributeStore.layerIds.map { x => Map("name" -> x.name, "zoom" -> x.zoom).asJava }.toArray

  def getValueClass(id: LayerId): String =
    attributeStore.readHeader[LayerHeader](id).valueClass

  def tileToMultiband[K](rdd: RDD[(K, Tile)]): RDD[(K, MultibandTile)] =
    rdd.map{ x => (x._1, MultibandTile(x._2)) }

  def read(
    keyType: String,
    layerName: String,
    zoom: Int,
    numPartitions: Int
  ): TiledRasterLayer[_] = {
    val id = LayerId(layerName, zoom)
    val valueClass = getValueClass(id)

    (keyType, valueClass) match {
      case ("SpatialKey", "geotrellis.raster.Tile") => {
        val result = layerReader.read[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](id, numPartitions)
        new SpatialTiledRasterLayer(Some(zoom), MultibandTileLayerRDD(tileToMultiband[SpatialKey](result), result.metadata))
      }
      case ("SpatialKey", "geotrellis.raster.MultibandTile") => {
        val result = layerReader.read[SpatialKey, MultibandTile, TileLayerMetadata[SpatialKey]](id, numPartitions)
        new SpatialTiledRasterLayer(Some(zoom), MultibandTileLayerRDD(result, result.metadata))
      }
      case ("SpaceTimeKey", "geotrellis.raster.Tile") => {
        val result = layerReader.read[SpaceTimeKey, Tile, TileLayerMetadata[SpaceTimeKey]](id, numPartitions)
        new TemporalTiledRasterLayer(Some(zoom), MultibandTileLayerRDD(tileToMultiband[SpaceTimeKey](result), result.metadata))
      }
      case ("SpaceTimeKey", "geotrellis.raster.MultibandTile") => {
        val result = layerReader.read[SpaceTimeKey, MultibandTile, TileLayerMetadata[SpaceTimeKey]](id, numPartitions)
        new TemporalTiledRasterLayer(Some(zoom), MultibandTileLayerRDD(result, result.metadata))
      }
    }
  }

  private def getTemporalQuery(queryIntervalStrings: ArrayList[String]) = {
    val temporalRanges = queryIntervalStrings
      .asScala
      .grouped(2)
      .map({ list =>
        list match {
          case mutable.Buffer(a, b) =>
            Between(ZonedDateTime.parse(a), ZonedDateTime.parse(b))
          case mutable.Buffer(a) => {
            val zdt = ZonedDateTime.parse(a)
            val zdt1 = zdt.minusNanos(16)
            val zdt2 = zdt.plusNanos(17)
            Between(zdt1, zdt2)
          }
        }})
      .toList

    if (temporalRanges.length >= 2) {
      val h1 = temporalRanges.head
      val h2 = temporalRanges.tail.head
      Some(temporalRanges.drop(2).foldLeft(h1 or h2)({ (cs, c) => cs or c }))
    }
    else if (temporalRanges.length == 1) {
      val h1 = temporalRanges.head
      Some(h1 or h1)
    }
    else None
  }

  def query(
    keyType: String,
    layerName: String,
    zoom: Int,
    queryGeometryBytes: Array[Byte],
    queryIntervalStrings: ArrayList[String],
    projQuery: String,
    numPartitions: Int
  ): TiledRasterLayer[_] = {
    val id = LayerId(layerName, zoom)
    val valueClass = getValueClass(id)
    val queryCRS = TileLayer.getCRS(projQuery)
    val spatialQuery = WKB.read(queryGeometryBytes)

    (keyType, valueClass) match {
      case ("SpatialKey", "geotrellis.raster.Tile") => {
        val layer = layerReader.query[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](id, numPartitions)
        val layerCRS = layer.result.metadata.crs
        val query = (queryCRS, spatialQuery) match {
          case (Some(crs), point: Point) => layer.where(Contains(point.reproject(layerCRS, crs)))
          case (None, point: Point) => layer.where(Contains(point))

          case (Some(crs), polygon: Polygon) => layer.where(Intersects(polygon.reproject(layerCRS, crs)))
          case (None, polygon: Polygon) => layer.where(Intersects(polygon))

          case (Some(crs), multi: MultiPolygon) => layer.where(Intersects(multi.reproject(layerCRS, crs)))
          case (None, multi: MultiPolygon) => layer.where(Intersects(multi))

          case _ => layer
        }

        val result = tileToMultiband[SpatialKey](query.result)

        new SpatialTiledRasterLayer(Some(zoom), MultibandTileLayerRDD(result, query.result.metadata))
      }

      case ("SpatialKey", "geotrellis.raster.MultibandTile") => {
        val layer = layerReader.query[SpatialKey, MultibandTile, TileLayerMetadata[SpatialKey]](id, numPartitions)
        val layerCRS = layer.result.metadata.crs
        val query = (queryCRS, spatialQuery) match {
          case (Some(crs), polygon: Polygon) => layer.where(Intersects(polygon.reproject(layerCRS, crs)))
          case (None, polygon: Polygon) => layer.where(Intersects(polygon))

          case (Some(crs), multi: MultiPolygon) => layer.where(Intersects(multi.reproject(layerCRS, crs)))
          case (None, multi: MultiPolygon) => layer.where(Intersects(multi))

          case _ => layer
        }
        new SpatialTiledRasterLayer(Some(zoom), query.result)
      }

      case ("SpaceTimeKey", "geotrellis.raster.Tile") => {
        val temporalQuery = getTemporalQuery(queryIntervalStrings)

        val layer = layerReader.query[SpaceTimeKey, Tile, TileLayerMetadata[SpaceTimeKey]](id, numPartitions)
        val layerCRS = layer.result.metadata.crs
        val query1 = (queryCRS, spatialQuery) match {
          case (Some(crs), polygon: Polygon) => layer.where(Intersects(polygon.reproject(layerCRS, crs)))
          case (None, polygon: Polygon) => layer.where(Intersects(polygon))

          case (Some(crs), multi: MultiPolygon) => layer.where(Intersects(multi.reproject(layerCRS, crs)))
          case (None, multi: MultiPolygon) => layer.where(Intersects(multi))

          case _ => layer
        }
        val query2 = temporalQuery match {
          case Some(q) => query1.where(q)
          case None => query1
        }
        val result = tileToMultiband[SpaceTimeKey](query2.result)

        new TemporalTiledRasterLayer(Some(zoom), MultibandTileLayerRDD(result, query2.result.metadata))
      }

      case ("SpaceTimeKey", "geotrellis.raster.MultibandTile") => {
        val temporalQuery = getTemporalQuery(queryIntervalStrings)

        val layer = layerReader.query[SpaceTimeKey, MultibandTile, TileLayerMetadata[SpaceTimeKey]](id, numPartitions)
        val layerCRS = layer.result.metadata.crs
        val query1 = (queryCRS, spatialQuery) match {
          case (Some(crs), polygon: Polygon) => layer.where(Intersects(polygon.reproject(layerCRS, crs)))
          case (None, polygon: Polygon) => layer.where(Intersects(polygon))

          case (Some(crs), multi: MultiPolygon) => layer.where(Intersects(multi.reproject(layerCRS, crs)))
          case (None, multi: MultiPolygon) => layer.where(Intersects(multi))

          case _ => layer
        }
        val query2 = temporalQuery match {
          case Some(q) => query1.where(q)
          case None => query1
        }
        new TemporalTiledRasterLayer(Some(zoom), query2.result)
      }
    }
  }
}


/**
  * Wrapper for the AccumuloLayerReader class.
  */
class AccumuloLayerReaderWrapper(
  in: AccumuloInstance,
  as: AccumuloAttributeStore,
  sc: SparkContext
) extends FilteringLayerReaderWrapper {

  val attributeStore = as
  val layerReader = AccumuloLayerReader(in)(sc)
}

/**
  * Wrapper for the HBaseLayerReader class.
  */
class HBaseLayerReaderWrapper(as: HBaseAttributeStore, sc: SparkContext)
    extends FilteringLayerReaderWrapper {

  val attributeStore = as
  val layerReader = HBaseLayerReader(as)(sc)
}

/**
  * Wrapper for the CassandraLayerReader class.
  */
class CassandraLayerReaderWrapper(as: CassandraAttributeStore, sc: SparkContext)
    extends FilteringLayerReaderWrapper {

  val attributeStore = as
  val layerReader = CassandraLayerReader(as)(sc)
}

/**
  * Wrapper for the FileLayerReader class.
  */
class FileLayerReaderWrapper(as: FileAttributeStore, sc: SparkContext)
    extends FilteringLayerReaderWrapper {

  val attributeStore = as
  val layerReader = FileLayerReader(as)(sc)
}

/**
  * Wrapper for the S3LayerReader class.
  */
class S3LayerReaderWrapper(as: S3AttributeStore, sc: SparkContext)
    extends FilteringLayerReaderWrapper {

  val attributeStore = as
  val layerReader = S3LayerReader(as)(sc)
}

/**
  * Wrapper for the HadoopLayerReader class.
  */
class HadoopLayerReaderWrapper(as: HadoopAttributeStore, sc: SparkContext)
    extends FilteringLayerReaderWrapper {

  val attributeStore = as
  val layerReader = HadoopLayerReader(as)(sc)
}

/**
  * Interface for requesting layer reader wrappers.  This object is
  * easily accessible from PySpark.
  */
object LayerReaderFactory {

  def buildHadoop(hasw: HadoopAttributeStoreWrapper) =
    new HadoopLayerReaderWrapper(hasw.attributeStore, hasw.sparkContext)

  def buildS3(s3asw: S3AttributeStoreWrapper, sc: SparkContext) =
    new S3LayerReaderWrapper(s3asw.attributeStore, sc)

  def buildFile(fasw: FileAttributeStoreWrapper, sc: SparkContext) =
    new FileLayerReaderWrapper(fasw.attributeStore, sc)

  def buildCassandra(casw: CassandraAttributeStoreWrapper, sc: SparkContext) =
    new CassandraLayerReaderWrapper(casw.attributeStore, sc)

  def buildHBase(hbasw: HBaseAttributeStoreWrapper, sc: SparkContext) =
    new HBaseLayerReaderWrapper(hbasw.attributeStore, sc)

  def buildAccumulo(aasw: AccumuloAttributeStoreWrapper, sc: SparkContext) =
    new AccumuloLayerReaderWrapper(aasw.instance, aasw.attributeStore, sc)
}
