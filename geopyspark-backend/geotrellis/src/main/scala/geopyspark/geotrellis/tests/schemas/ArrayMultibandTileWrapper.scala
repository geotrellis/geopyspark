package geopyspark.geotrellis.tests.schemas

import protos.tileMessages._
import geopyspark.util._
import geopyspark.geotrellis._
import geopyspark.geotrellis.testkit._
import geotrellis.raster._
import geotrellis.spark._

import org.apache.spark._
import org.apache.spark.rdd.RDD
import org.apache.spark.api.java.JavaRDD

object ArrayMultibandTileWrapper extends Wrapper2[MultibandTile, ProtoMultibandTile] {
  def testOut(sc: SparkContext): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[MultibandTile, ProtoMultibandTile](testRdd(sc))

  def testIn(rdd: RDD[Array[Byte]]) =
    PythonTranslator.fromPython[MultibandTile, ProtoMultibandTile](rdd, ProtoMultibandTile.parseFrom)

  def testRdd(sc: SparkContext): RDD[MultibandTile] = {
    val tile = ByteArrayTile(Array[Byte](0, 0, 1, 1), 2, 2)

    val multi = Array(
      ArrayMultibandTile(tile, tile, tile),
      ArrayMultibandTile(tile, tile, tile),
      ArrayMultibandTile(tile, tile, tile))

    sc.parallelize(multi)
  }
}
