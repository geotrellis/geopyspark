package geopyspark.geotrellis.protobufs

import geopyspark.util.ProtoBufCodec
import protos.tileMessages._
import geotrellis.raster._


trait MultibandTileProtoBuf {
  import TileProtoBuf._
  implicit def multibandTileProtoBufCodec = new ProtoBufCodec[MultibandTile, ProtoMultibandTile] {
    def encode(tile: MultibandTile): ProtoMultibandTile = {
      val tiles = for (i <- 0 until tile.bandCount) yield tile.band(i)
      ProtoMultibandTile(tiles = tiles.map(tileProtoBufCodec.encode))
    }

    def decode(message: ProtoMultibandTile): MultibandTile =
      MultibandTile(message.tiles.map(tileProtoBufCodec.decode))
  }
}
