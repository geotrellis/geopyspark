package geopyspark.vectorpipe.io

import geopyspark.util._
import geopyspark.vectorpipe._

import vectorpipe._
import vectorpipe.osm._

import org.apache.spark._
import org.apache.spark.sql._

import scala.util.{Failure, Success => S}


object OSMReader {
  def read(
    ss: SparkSession,
    source: String
  ): FeaturesCollection =
    osm.fromORC(source)(ss) match {
      case Failure(e) => null
      case S((ns, ws, rs)) => FeaturesCollection(osm.features(ns, ws, rs))
    }
}
