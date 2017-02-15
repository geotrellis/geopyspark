package geopyspark.geotrellis.io.hadoop

import geopyspark.geotrellis._

import geotrellis.proj4._
import geotrellis.raster._
import geotrellis.vector._
import geotrellis.spark.io.hadoop._
import geotrellis.spark.io.avro._

import scala.collection.JavaConverters._
import java.util.Map

import org.apache.spark._
import org.apache.spark.rdd.RDD
import org.apache.spark.api.java.JavaRDD

import org.apache.hadoop.fs.Path


object HadoopGeoTiffRDDOptions {
  def default = HadoopGeoTiffRDD.Options.DEFAULT

  def setValues(javaMap: java.util.Map[String, Any]): HadoopGeoTiffRDD.Options = {
    val stringValues = Array("timeTag", "timeFormat")

    val (stringMap, intMap) = GeoTrellisUtils.convertToScalaMap(javaMap, stringValues)

    val crs: Option[CRS] =
      if (intMap.contains("crs"))
        Some(CRS.fromEpsgCode(intMap("crs")))
      else
        None

    HadoopGeoTiffRDD.Options(
      crs = crs,
      timeTag = stringMap.getOrElse("timeTag", default.timeTag),
      timeFormat = stringMap.getOrElse("timeFormat", default.timeFormat),
      maxTileSize = intMap.get("maxTileSize"),
      numPartitions = intMap.get("numPartitions"),
      chunkSize = intMap.get("chunkSize"))
  }
}


object HadoopGeoTiffRDDWrapper {
  def readSpatialSingleband(path: String, sc: SparkContext): (JavaRDD[Array[Byte]], String) =
    PythonTranslator.toPython(HadoopGeoTiffRDD.spatial(path)(sc))

  def readSpatialSingleband(path: String, options: java.util.Map[String, Any],
    sc: SparkContext): (JavaRDD[Array[Byte]], String) = {
    val hadoopOptions = HadoopGeoTiffRDDOptions.setValues(options)

    PythonTranslator.toPython(HadoopGeoTiffRDD.spatial(path, hadoopOptions)(sc))
  }

  def readSpatialMultiband(path: String, sc: SparkContext): (JavaRDD[Array[Byte]], String) =
    PythonTranslator.toPython(HadoopGeoTiffRDD.spatialMultiband(path)(sc))

  def readSpatialMultiband(path: String, options: java.util.Map[String, Any],
    sc: SparkContext): (JavaRDD[Array[Byte]], String) = {
    val hadoopOptions = HadoopGeoTiffRDDOptions.setValues(options)

    PythonTranslator.toPython(HadoopGeoTiffRDD.spatialMultiband(path, hadoopOptions)(sc))
  }

  def readSpaceTimeSingleband(path: Path, sc: SparkContext): (JavaRDD[Array[Byte]], String) =
    PythonTranslator.toPython(HadoopGeoTiffRDD.temporal(path)(sc))

  def readSpaceTimeSingleband(path: Path, options: java.util.Map[String, Any],
    sc: SparkContext): (JavaRDD[Array[Byte]], String) = {
    val hadoopOptions = HadoopGeoTiffRDDOptions.setValues(options)

    PythonTranslator.toPython(HadoopGeoTiffRDD.temporal(path, hadoopOptions)(sc))
  }

  def readSpaceTimeMultiband(path: Path, sc: SparkContext): (JavaRDD[Array[Byte]], String) =
    PythonTranslator.toPython(HadoopGeoTiffRDD.temporalMultiband(path)(sc))

  def readSpaceTimeMultiband(path: Path, options: java.util.Map[String, Any],
    sc: SparkContext): (JavaRDD[Array[Byte]], String) = {
    val hadoopOptions = HadoopGeoTiffRDDOptions.setValues(options)

    PythonTranslator.toPython(HadoopGeoTiffRDD.temporalMultiband(path, hadoopOptions)(sc))
  }
}
