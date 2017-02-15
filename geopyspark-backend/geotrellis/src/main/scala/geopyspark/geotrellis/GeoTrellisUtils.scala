package geopyspark.geotrellis

import geotrellis.proj4._
import geotrellis.raster._
import geotrellis.vector._
import geotrellis.spark._
import geotrellis.spark.tiling._

import org.apache.spark.rdd._

import scala.collection.JavaConverters._
import collection.JavaConversions._
import java.util.Map


object GeoTrellisUtils {
  def convertToScalaMap(
    javaMap: java.util.Map[String, Any],
    stringValues: Array[String]
  ): (scala.collection.Map[String, String], scala.collection.Map[String, Int]) = {
    val scalaMap = javaMap.asScala

    val intMap =
      scalaMap.filterKeys(x => !(stringValues.contains(x)))
        .mapValues(x => x.asInstanceOf[Int])

    val stringMap =
      scalaMap.filterKeys(x => stringValues.contains(x))
        .mapValues(x => x.asInstanceOf[String])

    (stringMap, intMap)
  }

  implicit class JavaListExtensions(l: java.util.List[java.util.Map[String, _]]) {
    def toLayoutDefinition: LayoutDefinition =
      LayoutDefinition(l(0).toExtent, l(1).toTileLayout)
  }

  implicit class JavaMapExtensions(m: java.util.Map[String, _]) {
    def toExtent: Extent = {
      val mappedExtent = m.mapValues(x => x.asInstanceOf[Double])
      Extent(
        mappedExtent("xmin"),
        mappedExtent("ymin"),
        mappedExtent("xmax"),
        mappedExtent("ymax"))
    }

    def toTileLayout: TileLayout = {
      val mappedLayout = m.mapValues(x => x.asInstanceOf[Int])

      TileLayout(
        mappedLayout("layoutCols"),
        mappedLayout("layoutRows"),
        mappedLayout("tileCols"),
        mappedLayout("tileRows"))
    }

    def toCrs: Option[CRS] =
      if (m.isEmpty)
        None
      else
        m.head.asInstanceOf[(String, String)] match {
          case ("projParams", projParams) => Some(CRS.fromString(projParams))
          case ("epsg", epsgString) => Some(CRS.fromName(s"EPSG:$epsgString"))
          case ("wktString", wktString) => Some(CRS.fromWKT(wktString))
          case (k, _) => throw new Exception(s"Cannot create CRS from $k")
        }

    def getLayoutDefinition: LayoutDefinition =
      m("layout").asInstanceOf[java.util.ArrayList[java.util.Map[String, _]]].toLayoutDefinition
  }


  implicit class ScalaMapExtensions(m: scala.collection.immutable.Map[String, Any]) {
    def toJavaMap: java.util.Map[String, Any] = {
      val convertedInner =
        m.mapValues(x =>
            x match {
              case a: scala.collection.immutable.Map[_, _] => mapAsJavaMap(a)
              case b: List[_] =>
                val result = b.map(value =>
                    mapAsJavaMap(value
                      .asInstanceOf[scala.collection.immutable.Map[String, _]]))

                result.asJava

              // If other types aren't catched, they'll either return as a
              // JavaObject or not at all
              case c: String  => c
              case d: Int => d
              case e: Double => e
            })

      mapAsJavaMap(convertedInner)
    }
  }


  implicit class ExtentExtensions(e: Extent) {
    def toMap: scala.collection.immutable.Map[String, Double] =
      scala.collection.immutable.Map(
        "xmin" -> e.xmin,
        "ymin" -> e.ymin,
        "xmax" -> e.xmax,
        "ymax" -> e.ymax)
  }


  implicit class TileLayoutExtensions(tl: TileLayout) {
    def toMap: scala.collection.immutable.Map[String, Int] =
      scala.collection.immutable.Map(
        "layoutCols" -> tl.layoutCols,
        "layoutRows" -> tl.layoutRows,
        "tileCols" -> tl.tileCols,
        "tileRows" -> tl.tileRows)
  }


  implicit class LayoutDefinitionExtensions(ld: LayoutDefinition) {
    def toList = List(ld.extent.toMap, ld.tileLayout.toMap)
  }


  implicit class TileLayerMetadataExtensions[K](m: TileLayerMetadata[K]) {
    def toJavaMap: java.util.Map[String, Any] =
      scala.collection.immutable.Map(
        "cellType" -> m.cellType.name,
        "layout" -> m.layout.toList,
        "extent" -> m.extent.toMap,
        "crs" -> m.crs.toProj4String,
        "bounds" -> m.bounds.get.toString
      ).toJavaMap
  }
}
