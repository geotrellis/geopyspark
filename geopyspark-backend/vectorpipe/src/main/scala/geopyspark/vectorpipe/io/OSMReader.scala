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
    source: String,
    view: String,
    loggingStrategy: String
  ): FeaturesCollection =
    osm.fromORC(source)(ss) match {
      case Failure(e) => null
      case S((ns, ws, rs)) =>
        if (view == VectorPipeConstants.SNAPSHOT)
          loggingStrategy match {
            case VectorPipeConstants.NOTHING =>
              FeaturesCollection(osm.snapshotFeatures(VectorPipe.logNothing, ns, ws, rs))
            case VectorPipeConstants.LOG4J =>
              FeaturesCollection(osm.snapshotFeatures(VectorPipe.logToLog4j, ns, ws, rs))
            case VectorPipeConstants.STD =>
              FeaturesCollection(osm.snapshotFeatures(VectorPipe.logToStdout, ns, ws, rs))
          }
        else
          FeaturesCollection(historicalFeatures(ns, ws))
    }
}
