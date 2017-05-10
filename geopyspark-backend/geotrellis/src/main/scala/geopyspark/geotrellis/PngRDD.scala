package geopyspark.geotrellis

import geotrellis.raster.render._
import geotrellis.spark._
import geotrellis.spark.render._


abstract class PngRDD[K: ClassTag](rdd: RDD[(K, Png)]) {
  def getNamedRamp(name: String): ColorRamp = ???
  def makeColorRamp(ramp: java.util.Map[Int, Int]): ColorRamp = ???
  def makeColorRamp(ramp: java.util.Map[Double, Int]): ColorRamp = ???

class SpatialPngRDD(rdd: RDD[(SpatialKey, Png)]) extends PngRDD {
  def lookup(col: Int, row: Int): Array[Array[Byte]] =
    rdd.lookup(SpatialKey(col, row)).map(_.bytes).toArray
}
