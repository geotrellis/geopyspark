package geopyspark.geotrellis.io

import geopyspark.geotrellis._

import geotrellis.raster._
import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.spark.io.accumulo._
import geotrellis.spark.io.cassandra._
import geotrellis.spark.io.file._
import geotrellis.spark.io.hadoop._
import geotrellis.spark.io.hbase._
import geotrellis.spark.io.index._
import geotrellis.spark.io.index.hilbert._
import geotrellis.spark.io.s3._
import geotrellis.vector._

import spray.json._

import org.apache.spark._
import org.apache.spark.api.java.JavaRDD
import org.apache.spark.rdd.RDD

import java.time.ZonedDateTime

import geopyspark.geotrellis.PythonTranslator


/**
  * Base wrapper class for all backends that provide a
  * LayerWriter[LayerId].
  */
abstract class LayerWriterWrapper {

  def attributeStore: AttributeStore
  def layerWriter: LayerWriter[LayerId]

  private def getSpatialIndexMethod(indexStrategy: String): KeyIndexMethod[SpatialKey] =
    indexStrategy match {
      case "zorder" => ZCurveKeyIndexMethod
      case "hilbert" => HilbertKeyIndexMethod
      case "rowmajor" => RowMajorKeyIndexMethod
      case _ => throw new Exception
    }

  private def getTemporalIndexMethod(
    timeString: String,
    indexStrategy: String) =
    (indexStrategy, timeString) match {
      case ("zorder", "millis") => ZCurveKeyIndexMethod.byMilliseconds(1)
      case ("zorder", "seconds") => ZCurveKeyIndexMethod.bySecond
      case ("zorder", "minutes") => ZCurveKeyIndexMethod.byMinute
      case ("zorder", "hours") => ZCurveKeyIndexMethod.byHour
      case ("zorder", "days") => ZCurveKeyIndexMethod.byDay
      case ("zorder", "months") => ZCurveKeyIndexMethod.byMonth
      case ("zorder", "years") => ZCurveKeyIndexMethod.byYear
      case ("hilbert", _) => {
        timeString.split(",") match {
          case Array(minDate, maxDate, resolution) =>
            HilbertKeyIndexMethod(ZonedDateTime.parse(minDate),
              ZonedDateTime.parse(maxDate),
              resolution.toInt)
          case Array(resolution) =>
            HilbertKeyIndexMethod(resolution.toInt)
          case _ => throw new Exception(s"Invalid timeString: $timeString")
        }
      }
      case _ => throw new Exception
    }

  def write(
    layerName: String,
    tiledRasterRDD: TiledRasterRDD[_],
    timeString: String,
    indexStrategy: String
  ): Unit ={
    val id = LayerId(layerName, tiledRasterRDD.getZoom)

    tiledRasterRDD match {
      case spatial: SpatialTiledRasterRDD => {
        val indexMethod = getSpatialIndexMethod(indexStrategy)
        layerWriter.write(id, spatial.rdd, indexMethod)
      }
      case temporal: TemporalTiledRasterRDD => {
        val indexMethod = getTemporalIndexMethod(timeString, indexStrategy)
        layerWriter.write(id, temporal.rdd, indexMethod)
      }
    }
  }

  def write(
    layerName: String,
    tiledRasterRDD: Seq[TiledRasterRDD[_]],
    timeString: String,
    indexStrategy: String
  ): Unit =
    // TODO: Find a way to iterate through the sequence without checking the type for each tiledRasterRDD
    tiledRasterRDD.foreach { tiledRDD => write(layerName, tiledRDD, timeString, indexStrategy) }
}


/**
  * Wrapper for the AccumuloLayerReader class.
  */
class AccumuloLayerWriterWrapper(
  in: AccumuloInstance,
  as: AccumuloAttributeStore,
  table: String
) extends LayerWriterWrapper {

  val attributeStore = as
  val layerWriter = AccumuloLayerWriter(in, as, table)
}

/**
  * Wrapper for the HBaseLayerReader class.
  */
class HBaseLayerWriterWrapper(
  as: HBaseAttributeStore,
  table: String
) extends LayerWriterWrapper {

  val attributeStore = as
  val layerWriter = HBaseLayerWriter(as, table)
}

/**
  * Wrapper for the CassandraLayerReader class.
  */
class CassandraLayerWriterWrapper(
  as: CassandraAttributeStore,
  ks: String,
  table: String
) extends LayerWriterWrapper {

  val attributeStore = as
  val layerWriter = CassandraLayerWriter(as, ks, table)
}

/**
  * Wrapper for the FileLayerReader class.
  */
class FileLayerWriterWrapper(as: FileAttributeStore)
    extends LayerWriterWrapper {

  val attributeStore = as
  val layerWriter = FileLayerWriter(as)
}

/**
  * Wrapper for the S3LayerReader class.
  */
class S3LayerWriterWrapper(as: S3AttributeStore)
    extends LayerWriterWrapper {

  val attributeStore = as
  val layerWriter = S3LayerWriter(as)
}

/**
  * Wrapper for the HadoopLayerReader class.
  */
class HadoopLayerWriterWrapper(as: HadoopAttributeStore)
    extends LayerWriterWrapper {

  val attributeStore = as
  val layerWriter = HadoopLayerWriter(as.rootPath, as)
}

/**
  * Interface for requesting layer writer wrappers.  This object is
  * easily accessible from PySpark.
  */
object LayerWriterFactory {

  def buildHadoop(hasw: HadoopAttributeStoreWrapper) =
    new HadoopLayerWriterWrapper(hasw.attributeStore)

  def buildS3(s3asw: S3AttributeStoreWrapper) =
    new S3LayerWriterWrapper(s3asw.attributeStore)

  def buildFile(fasw: FileAttributeStoreWrapper) =
    new FileLayerWriterWrapper(fasw.attributeStore)

  def buildCassandra(casw: CassandraAttributeStoreWrapper) =
    new CassandraLayerWriterWrapper(
      casw.attributeStore,
      casw.keySpace,
      casw.table
    )

  def buildHBase(hbasw: HBaseAttributeStoreWrapper) =
    new HBaseLayerWriterWrapper(hbasw.attributeStore, hbasw.table)

  def buildAccumulo(aasw: AccumuloAttributeStoreWrapper) =
    new AccumuloLayerWriterWrapper(aasw.instance, aasw.attributeStore, aasw.table)
}
