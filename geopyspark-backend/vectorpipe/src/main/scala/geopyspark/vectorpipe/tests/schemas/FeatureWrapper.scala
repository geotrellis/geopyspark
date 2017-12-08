package geopyspark.vectorpipe.tests.schemas

import geopyspark.util._
import geopyspark.vectorpipe._

import geotrellis.vector._

import vectorpipe.osm._

import protos.featureMessages._

import org.apache.spark._
import org.apache.spark.rdd._
import org.apache.spark.api.java.JavaRDD

import java.time._


object FeatureWrapper {
  def testOut(sc: SparkContext): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[Feature[Geometry, ElementMeta], ProtoFeature](testRDD(sc))

  def testIn(rdd: RDD[Array[Byte]]) =
    PythonTranslator.fromPython[Feature[Geometry, ElementMeta], ProtoFeature](rdd, ProtoFeature.parseFrom)

  def testRDD(sc: SparkContext): RDD[Feature[Geometry, ElementMeta]] = {
    val points: Seq[Point] = for (x <- 0 until 10) yield Point(x, x + 2)
    val lines: Seq[Line] = points.grouped(5).map { Line(_) }.toSeq
    val multiLines = MultiLine(lines)

    val tags: Map[String, String] =
      Map(
        "amenity" -> "embassy",
        "diplomatic" -> "embassy",
        "country" -> "azavea"
      )

    val elemMeta =
      ElementMeta(
        id = 1993.toLong,
        user = "Jake",
        uid = 19144.toLong,
        changeset = 10.toLong,
        version = 24.toLong,
        minorVersion = 5.toLong,
        timestamp = Instant.parse("2012-06-05T07:00:00Z"),
        visible = true,
        tags = tags)

    sc.parallelize(
      Array(
        Feature(multiLines, elemMeta),
        Feature(lines.head, elemMeta),
        Feature(points.head, elemMeta)
      )
    )
  }
}
