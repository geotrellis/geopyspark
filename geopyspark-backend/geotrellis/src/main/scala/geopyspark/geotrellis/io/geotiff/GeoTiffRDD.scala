package geopyspark.geotrellis.io.geotiff

import geopyspark.translator._
import geopyspark.geotrellis._

import geotrellis.proj4._
import geotrellis.spark.io.avro._
import geotrellis.spark.io.hadoop._
import geotrellis.spark.io.s3._
import geotrellis.spark.io.s3.testkit._

import scala.collection.JavaConversions._

import java.net.URI
import scala.reflect._

import org.apache.spark._
import org.apache.hadoop.fs.Path


object GeoTiffRDD {
  import Constants._

  object HadoopGeoTiffRDDOptions {
    def default = HadoopGeoTiffRDD.Options.DEFAULT

    def setValues(
      intMap: Map[String, Int],
      stringMap: Map[String, String],
      partitionBytes: Option[Long]
    ): HadoopGeoTiffRDD.Options = {
      val crs: Option[CRS] =
        if (stringMap.contains("crs"))
          TileLayer.getCRS(stringMap("crs"))
        else
          None

      HadoopGeoTiffRDD.Options(
        crs = crs,
        timeTag = stringMap.getOrElse("time_tag", default.timeTag),
        timeFormat = stringMap.getOrElse("time_format", default.timeFormat),
        maxTileSize = intMap.get("max_tile_size"),
        numPartitions = intMap.get("num_partitions"),
        partitionBytes = partitionBytes,
        chunkSize = intMap.get("chunk_size")
      )
    }
  }

  object S3GeoTiffRDDOptions {
    def default = S3GeoTiffRDD.Options.DEFAULT

    def setValues(
      intMap: Map[String, Int],
      stringMap: Map[String, String],
      partitionBytes: Option[Long]
    ): S3GeoTiffRDD.Options = {
      val crs: Option[CRS] =
        if (stringMap.contains("crs"))
          TileLayer.getCRS(stringMap("crs"))
        else
          None

      val getS3Client: () => S3Client =
        stringMap.get("s3_client") match {
          case Some(client) =>
            if (client == "default")
              default.getS3Client
            else if (client == "mock")
              () => new MockS3Client()
            else
              throw new Error(s"Could not find the given S3Client, $client")
          case None => default.getS3Client
        }

      S3GeoTiffRDD.Options(
        crs = crs,
        timeTag = stringMap.getOrElse("time_tag", default.timeTag),
        timeFormat = stringMap.getOrElse("time_format", default.timeFormat),
        maxTileSize = intMap.get("max_tile_size"),
        numPartitions = intMap.get("num_partitions"),
        partitionBytes = partitionBytes,
        chunkSize = intMap.get("chunk_size"),
        delimiter = stringMap.get("delimiter"),
        getS3Client = getS3Client
      )
    }
  }

  def get(
    sc: SparkContext,
    keyType: String,
    paths: java.util.List[String],
    options: java.util.Map[String, Any],
    partitionBytes: String
  ): RasterLayer[_] = {
    val uris = paths.map{ path => new URI(path) }
    val (stringMap, intMap) = GeoTrellisUtils.convertToScalaMap(options)
    val bytes = Some(partitionBytes.toLong)

    uris
      .map { uri =>
        uri.getScheme match {
          case S3 =>
            getS3GeoTiffRDD(
              sc,
              keyType,
              uri,
              S3GeoTiffRDDOptions.setValues(intMap, stringMap, bytes)
            )
          case _ =>
              getHadoopGeoTiffRDD(
                sc,
                keyType,
                new Path(uri),
                HadoopGeoTiffRDDOptions.setValues(intMap, stringMap, bytes)
              )
        }
      }
      .reduce{ (r1, r2) =>
        keyType match {
          case PROJECTEDEXTENT =>
            ProjectedRasterLayer(r1.asInstanceOf[ProjectedRasterLayer].rdd.union(r2.asInstanceOf[ProjectedRasterLayer].rdd))
          case TEMPORALPROJECTEDEXTENT =>
            TemporalRasterLayer(r1.asInstanceOf[TemporalRasterLayer].rdd.union(r2.asInstanceOf[TemporalRasterLayer].rdd))
        }
      }
  }

  private def getHadoopGeoTiffRDD(
    sc: SparkContext,
    keyType: String,
    path: Path,
    options: HadoopGeoTiffRDD.Options
  ): RasterLayer[_] =
    keyType match {
      case PROJECTEDEXTENT =>
        ProjectedRasterLayer(HadoopGeoTiffRDD.spatialMultiband(path, options)(sc))
      case TEMPORALPROJECTEDEXTENT =>
        TemporalRasterLayer(HadoopGeoTiffRDD.temporalMultiband(path, options)(sc))
    }

  private def getS3GeoTiffRDD(
    sc: SparkContext,
    keyType: String,
    uri: URI,
    options: S3GeoTiffRDD.Options
  ): RasterLayer[_] =
    keyType match {
      case PROJECTEDEXTENT =>
        ProjectedRasterLayer(S3GeoTiffRDD.spatialMultiband(uri.getHost, uri.getPath.tail, options)(sc))
      case TEMPORALPROJECTEDEXTENT =>
        TemporalRasterLayer(S3GeoTiffRDD.temporalMultiband(uri.getHost, uri.getPath.tail, options)(sc))
    }
}
