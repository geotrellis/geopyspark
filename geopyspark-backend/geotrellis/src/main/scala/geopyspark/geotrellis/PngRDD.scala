package geopyspark.geotrellis

import org.apache.spark.rdd.RDD

import geotrellis.raster._
import geotrellis.raster.histogram._
import geotrellis.raster.render._
import geotrellis.spark._
import geotrellis.spark.render._

import scala.reflect._

object Coloring {
  def getNamedRamp(name: String): ColorRamp = {
    name match {
      case "hot" => ColorRamps.HeatmapDarkRedToYellowWhite
      case "coolwarm" => ColorRamps.BlueToRed
      case "magma" => ColorRamps.Magma
      case "inferno" => ColorRamps.Inferno
      case "plasma" => ColorRamps.Plasma
      case "viridis" => ColorRamps.Viridis

      case "BlueToOrange" => ColorRamps.BlueToOrange
      case "LightYellowToOrange" => ColorRamps.LightYellowToOrange
      case "BlueToRed" => ColorRamps.BlueToRed
      case "GreenToRedOrange" => ColorRamps.GreenToRedOrange
      case "LightToDarkSunset" => ColorRamps.LightToDarkSunset
      case "LightToDarkGreen" => ColorRamps.LightToDarkGreen
      case "HeatmapYellowToRed" => ColorRamps.HeatmapYellowToRed
      case "HeatmapBlueToYellowToRedSpectrum" => ColorRamps.HeatmapBlueToYellowToRedSpectrum
      case "HeatmapDarkRedToYellowWhite" => ColorRamps.HeatmapDarkRedToYellowWhite
      case "HeatmapLightPurpleToDarkPurpleToWhite" => ColorRamps.HeatmapLightPurpleToDarkPurpleToWhite
      case "ClassificationBoldLandUse" => ColorRamps.ClassificationBoldLandUse
      case "ClassificationMutedTerrain" => ColorRamps.ClassificationMutedTerrain
      case "Magma" => ColorRamps.Magma
      case "Inferno" => ColorRamps.Inferno
      case "Plasma" => ColorRamps.Plasma
      case "Viridis" => ColorRamps.Viridis
    }
  }

  def makeColorMap(breaks: Array[Int], name: String): ColorMap = ColorMap(breaks, getNamedRamp(name))
  def makeColorMap(breaks: Array[Double], name: String): ColorMap = ColorMap(breaks, getNamedRamp(name))

  def makeColorMap(hist: Histogram[Int], name: String): ColorMap = ColorMap.fromQuantileBreaks(hist, getNamedRamp(name))
  def makeColorMap(hist: Histogram[Double], name: String)(implicit dummy: DummyImplicit): ColorMap = ColorMap.fromQuantileBreaks(hist, getNamedRamp(name))

}

object ColorRamp {
  def get(name: String): Array[Int] =
    Coloring.getNamedRamp(name).colors.toArray

  def get(name: String, numColors: Int): Array[Int] =
    Coloring.getNamedRamp(name).stops(numColors).colors.toArray

  def getHex(name: String): Array[String] =
    get(name).map(x => s"#${x.toHexString.toUpperCase}")

  def getHex(name: String, numColors: Int): Array[String] =
    get(name, numColors).map(x => s"#${x.toHexString.toUpperCase}")
}

abstract class PngRDD[K: SpatialComponent :ClassTag] {
  def rdd: RDD[(K, Png)]
}

object PngRDD {
  def asSingleband(tiled: SpatialTiledRasterRDD, rampName: String): SpatialPngRDD = {
    val rdd = tiled.rdd
    val histogram = rdd.histogram().head
    val mapped = rdd.map({ case (key, mbtile) =>
      val tile = mbtile
        .band(0)
        .renderPng(Coloring.makeColorMap(histogram, rampName))
      key -> tile
    })
    new SpatialPngRDD(mapped.asInstanceOf[RDD[(tiled.keyType, Png)]])
  }

  def asSingleband(tiled: TemporalTiledRasterRDD, rampName: String): TemporalPngRDD = {
    val rdd = tiled.rdd
    val histogram = rdd.histogram().head
    val mapped = rdd.map({ case (key, mbtile) =>
      val tile = mbtile
        .band(0)
        .renderPng(Coloring.makeColorMap(histogram, rampName))
      key -> tile
    })
    new TemporalPngRDD(mapped.asInstanceOf[RDD[(tiled.keyType, Png)]])
  }

}

class SpatialPngRDD(val rdd: RDD[(SpatialKey, Png)]) extends PngRDD[SpatialKey] {
  def lookup(col: Int, row: Int): Array[Array[Byte]] =
    rdd.lookup(SpatialKey(col, row)).map(_.bytes).toArray
}

class TemporalPngRDD(val rdd: RDD[(SpaceTimeKey, Png)]) extends PngRDD[SpaceTimeKey] {
  def lookup(col: Int, row: Int, instant: Long): Array[Array[Byte]] =
    rdd.lookup(SpaceTimeKey(col, row, instant)).map(_.bytes).toArray
}
