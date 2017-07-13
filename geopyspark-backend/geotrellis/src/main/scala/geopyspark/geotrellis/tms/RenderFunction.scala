package geopyspark.geotrellis.tms

import geotrellis.raster._
import geotrellis.raster.render._

trait TileRender {
  def requiresEncoding(): Boolean
  def render(tile: MultibandTile): Array[Byte] = ???
  def renderEncoded(buffer: Array[Byte]): Array[Byte] = ???
}

class RenderFromCM(cm: ColorMap) extends TileRender {
  def requiresEncoding() = false
  override def render(tile: MultibandTile) = tile.band(0).renderPng(cm).bytes
}
