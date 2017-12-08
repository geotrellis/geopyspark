package geopyspark.geotrellis.tests.schemas

import geopyspark.util._
import geopyspark.geotrellis._
import protos.keyMessages._
import geopyspark.geotrellis.testkit._
import geotrellis.spark._

import org.apache.spark._
import org.apache.spark.rdd.RDD
import org.apache.spark.api.java.JavaRDD

object SpatialKeyWrapper extends Wrapper2[SpatialKey, ProtoSpatialKey] {
  def testOut(sc: SparkContext): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[SpatialKey, ProtoSpatialKey](testRdd(sc))

  def testIn(rdd: RDD[Array[Byte]]) =
    PythonTranslator.fromPython[SpatialKey, ProtoSpatialKey](rdd, ProtoSpatialKey.parseFrom)

  def testRdd(sc: SparkContext): RDD[SpatialKey] = {
    val arr = Array(
      SpatialKey(7,3))
    sc.parallelize(arr)
  }
}
