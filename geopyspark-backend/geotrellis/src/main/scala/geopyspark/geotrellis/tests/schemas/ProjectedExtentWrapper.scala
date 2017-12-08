package geopyspark.geotrellis.tests.schemas

import geopyspark.util._
import geopyspark.geotrellis._
import protos.extentMessages._

import geopyspark.geotrellis.testkit._

import geotrellis.proj4._
import geotrellis.vector._
import geotrellis.spark._
import geotrellis.spark.io._

import org.apache.spark._
import org.apache.spark.rdd.RDD
import org.apache.spark.api.java.JavaRDD

object ProjectedExtentWrapper extends Wrapper2[ProjectedExtent, ProtoProjectedExtent]{
  def testOut(sc: SparkContext): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[ProjectedExtent, ProtoProjectedExtent](testRdd(sc))

  def testIn(rdd: RDD[Array[Byte]]) =
    PythonTranslator.fromPython[ProjectedExtent, ProtoProjectedExtent](rdd, ProtoProjectedExtent.parseFrom)

  def testRdd(sc: SparkContext): RDD[ProjectedExtent] = {
    val arr = Array(
      ProjectedExtent(Extent(0, 0, 1, 1), CRS.fromEpsgCode(2004)),
      ProjectedExtent(Extent(1, 2, 3, 4), CRS.fromEpsgCode(2004)),
      ProjectedExtent(Extent(5, 6, 7, 8), CRS.fromEpsgCode(2004)))
    sc.parallelize(arr)
  }
}
