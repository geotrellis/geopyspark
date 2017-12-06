package geopyspark.geotrellis.tests.schemas

import geopyspark.util._
import geopyspark.geotrellis._
import protos.extentMessages._
import geopyspark.geotrellis.testkit._

import geotrellis.vector.Extent
import geotrellis.spark._

import org.apache.spark._
import org.apache.spark.rdd.RDD
import org.apache.spark.api.java.JavaRDD

object ExtentWrapper extends Wrapper2[Extent, ProtoExtent]{
  def testOut(sc: SparkContext): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[Extent, ProtoExtent](testRdd(sc))
  def testIn(rdd: RDD[Array[Byte]]) =
    PythonTranslator.fromPython[Extent, ProtoExtent](rdd, ProtoExtent.parseFrom)

  def testRdd(sc: SparkContext): RDD[Extent] = {
    val arr = Array(
      Extent(0, 0, 1, 1),
      Extent(1, 2, 3, 4),
      Extent(5, 6, 7, 8))
    sc.parallelize(arr)
  }
}
