package geopyspark.geotrellis.tests.schemas

import geopyspark.util._
import geopyspark.geotrellis._
import protos.extentMessages._
import geopyspark.geotrellis.testkit._

import geotrellis.proj4._
import geotrellis.vector.Extent
import geotrellis.spark._
import geotrellis.spark.io._

import org.apache.spark._
import org.apache.spark.rdd.RDD
import org.apache.spark.api.java.JavaRDD

import java.time.Instant


object TemporalProjectedExtentWrapper extends Wrapper2[TemporalProjectedExtent, ProtoTemporalProjectedExtent]{
  def testOut(sc: SparkContext): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[TemporalProjectedExtent, ProtoTemporalProjectedExtent](testRdd(sc))
  def testIn(rdd: RDD[Array[Byte]]) =
    PythonTranslator.fromPython[TemporalProjectedExtent, ProtoTemporalProjectedExtent](rdd, ProtoTemporalProjectedExtent.parseFrom)

  def testRdd(sc: SparkContext): RDD[TemporalProjectedExtent] = {
    val arr = Array(
      TemporalProjectedExtent(Extent(0, 0, 1, 1), CRS.fromEpsgCode(2004), Instant.parse("2016-08-24T09:00:00Z").toEpochMilli),
      TemporalProjectedExtent(Extent(1, 2, 3, 4), CRS.fromEpsgCode(2004), Instant.parse("2016-08-24T09:00:00Z").toEpochMilli),
      TemporalProjectedExtent(Extent(5, 6, 7, 8), CRS.fromEpsgCode(2004), Instant.parse("2016-08-24T09:00:00Z").toEpochMilli))
    sc.parallelize(arr)
  }
}
