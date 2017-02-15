package geopyspark.geotrellis.spark.tiling

import geopyspark.geotrellis.GeoTrellisUtils._

import geotrellis.raster.resample._
import geotrellis.spark.tiling._

import org.apache.spark._

import scala.collection.JavaConverters._
import collection.JavaConversions._
import java.util.Map


object TilerOptions {
  def default = Tiler.Options.DEFAULT

  def getResampleMethod(resampleMethod: Option[String]): ResampleMethod =
    resampleMethod match {
      case None => default.resampleMethod
      case Some(x) =>
        if (x == "NearestNeighbor")
          NearestNeighbor
        else if (x == "Bilinear")
          Bilinear
        else if (x == "CubicConvolution")
          CubicConvolution
        else if (x == "CubicSpline")
          CubicSpline
        else if (x == "Lanczos")
          Lanczos
        else if (x == "Average")
          Average
        else if (x == "Mode")
          Mode
        else if (x == "Median")
          Median
        else if (x == "Max")
          Max
        else if (x == "Min")
          Min
        else
          throw new Exception(s"$x, Is not a known sampling method")
    }

  def setValues(javaMap: java.util.Map[String, Any]): Tiler.Options = {
    val stringValues = Array("resampleMethod", "partitioner")
    val scalaMap = javaMap.asScala

    val intMap =
      scalaMap.filterKeys(x => !(stringValues.contains(x)))
        .mapValues(x => x.asInstanceOf[Int])

    val stringMap =
      scalaMap.filterKeys(x => stringValues.contains(x))
        .mapValues(x => x.asInstanceOf[String])

    val resampleMethod = getResampleMethod(stringMap.get("resampleMethod"))

    val partitioner: Option[Partitioner] =
      stringMap.get("partitioer") match {
        case None => None
        case Some(x) =>
          intMap.get("numPartitions") match {
            case None => None
            case Some(num) =>
              if (x == "HashPartitioner")
                Some(new HashPartitioner(num))
              else
                throw new Exception(s"$x, Is not a known Partitioner")
          }
      }

    Tiler.Options(
      resampleMethod = resampleMethod,
      partitioner = partitioner)
  }
}
