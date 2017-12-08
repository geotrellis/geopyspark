package geopyspark.vectorpipe.tests.schemas

import geopyspark.util._
import geopyspark.vectorpipe._

import geotrellis.vector._
import geotrellis.raster.rasterize._

import vectorpipe.osm._

import protos.featureMessages._

import org.apache.spark._
import org.apache.spark.rdd._
import org.apache.spark.api.java.JavaRDD

import java.time._


object FeatureCellValueWrapper {
  def testOut(sc: SparkContext): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[Feature[Geometry, CellValue], ProtoFeatureCellValue](testRDD(sc))

  def testIn(rdd: RDD[Array[Byte]]) =
    PythonTranslator.fromPython[Feature[Geometry, CellValue], ProtoFeatureCellValue](rdd, ProtoFeatureCellValue.parseFrom)

  def testRDD(sc: SparkContext): RDD[Feature[Geometry, CellValue]] = {
    val points: Seq[Point] = for (x <- 0 until 10) yield Point(x, x + 2)
    val lines: Seq[Line] = points.grouped(5).map { Line(_) }.toSeq
    val multiLines = MultiLine(lines)

    sc.parallelize(
      Array(
        Feature(multiLines, CellValue(1, 0)),
        Feature(lines.head, CellValue(1, 0)),
        Feature(points.head, CellValue(2, 1))
      )
    )
  }
}
