package geopyspark.geotrellis.tests.schemas

import protos.tileMessages._
import protos.extentMessages._
import protos.tupleMessages._

import geopyspark.util._
import geopyspark.geotrellis._
import geopyspark.geotrellis.testkit._

import geotrellis.proj4._
import geotrellis.raster._
import geotrellis.vector._
import geotrellis.spark._

import org.apache.spark._
import org.apache.spark.rdd.RDD
import org.apache.spark.api.java.JavaRDD

object TupleWrapper extends Wrapper2[(ProjectedExtent, MultibandTile), ProtoTuple]{
  def testOut(sc: SparkContext): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(ProjectedExtent, MultibandTile), ProtoTuple](testRdd(sc))

  def testIn(rdd: RDD[Array[Byte]]) =
    PythonTranslator.fromPython[(ProjectedExtent, MultibandTile), ProtoTuple](rdd,
      ProtoTuple.parseFrom)

  def testRdd(sc: SparkContext): RDD[(ProjectedExtent, MultibandTile)] = {
    val tile = ByteArrayTile(Array[Byte](0, 0, 1, 1), 2, 2)
    val multiband = ArrayMultibandTile(tile, tile, tile)
    val proj = ProjectedExtent(Extent(0, 0, 1, 1), CRS.fromEpsgCode(2004))

    val arr = Array(
      (proj, multiband),
      (proj, multiband),
      (proj, multiband))
    sc.parallelize(arr)
  }
}
