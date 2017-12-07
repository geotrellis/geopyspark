package geopyspark.vectorpipe

import geopyspark.util._
import geopyspark.vectorpipe._
import protos.featureMessages._

import geotrellis.vector._

import vectorpipe._
import vectorpipe.osm._

import org.apache.spark.rdd._
import org.apache.spark.api.java.JavaRDD

import spray.json._
import DefaultJsonProtocol._


class FeaturesCollection(
  val points: RDD[Feature[Point, ElementMeta]],
  val lines: RDD[Feature[Line, ElementMeta]],
  val polygons: RDD[Feature[Polygon, ElementMeta]],
  val multiPolygons: RDD[Feature[MultiPolygon, ElementMeta]]
) {

  def toProtoPoints: JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[Feature[Geometry, ElementMeta], ProtoFeature](points.asInstanceOf[RDD[Feature[Geometry, ElementMeta]]])

  def toProtoLines: JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[Feature[Geometry, ElementMeta], ProtoFeature](lines.asInstanceOf[RDD[Feature[Geometry, ElementMeta]]])

  def toProtoPolygons: JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[Feature[Geometry, ElementMeta], ProtoFeature](polygons.asInstanceOf[RDD[Feature[Geometry, ElementMeta]]])

  def toProtoMultiPolygons: JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[Feature[Geometry, ElementMeta], ProtoFeature](multiPolygons.asInstanceOf[RDD[Feature[Geometry, ElementMeta]]])

  def getPointTags: String =
    points
      .map { _.data.tags }
      .reduce { _ ++: _ }
      .toJson
      .compactPrint

  def getLineTags: String =
    lines
      .map { _.data.tags }
      .reduce { _ ++: _ }
      .toJson
      .compactPrint

  def getPolygonTags: String =
    polygons
      .map { _.data.tags }
      .reduce { _ ++: _ }
      .toJson
      .compactPrint

  def getMultiPolygonTags: String =
    multiPolygons
      .map { _.data.tags }
      .reduce { _ ++: _ }
      .toJson
      .compactPrint
}


object FeaturesCollection {
  def apply(features: Features): FeaturesCollection =
    new FeaturesCollection(features.points, features.lines, features.polygons, features.multiPolys)

  def apply(
    points: RDD[Feature[Point, ElementMeta]],
    lines: RDD[Feature[Line, ElementMeta]],
    polygons: RDD[Feature[Polygon, ElementMeta]],
    multiPolygons: RDD[Feature[MultiPolygon, ElementMeta]]
  ): FeaturesCollection =
    new FeaturesCollection(points, lines, polygons, multiPolygons)
}
