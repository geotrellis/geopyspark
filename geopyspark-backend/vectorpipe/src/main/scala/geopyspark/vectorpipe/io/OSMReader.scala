package geopyspark.vectorpipe.io

import geopyspark.util._
import geopyspark.vectorpipe._

import vectorpipe._
import vectorpipe.osm.{OSMReader => OSM}

import org.apache.spark._
import org.apache.spark.sql._

import java.net.URI


object OSMReader {
  def fromORC(
    ss: SparkSession,
    sourcePath: String,
    cachePath: String
  ): FeaturesCollection = {
    val reader =
      cachePath match {
        case s: String => OSM(new URI(sourcePath), s)(ss)
        case null => OSM(new URI(sourcePath))(ss)
      }

    FeaturesCollection(
      reader.pointFeaturesRDD,
      reader.lineFeaturesRDD,
      reader.polygonFeaturesRDD,
      reader.multiPolygonFeaturesRDD
    )
  }

  def fromDataFrame(
    elements: Dataset[Row],
    cachePath: String
  ): FeaturesCollection = {
    val reader =
      cachePath match {
        case s: String => new OSM(elements, Some(new URI(s)), None)(elements.sparkSession)
        case null => new OSM(elements, None, None)(elements.sparkSession)
      }

    FeaturesCollection(
      reader.pointFeaturesRDD,
      reader.lineFeaturesRDD,
      reader.polygonFeaturesRDD,
      reader.multiPolygonFeaturesRDD
    )
  }
}
