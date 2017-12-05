package geopyspark.translator.protobufs

import geopyspark.translator.ProtoBufCodec
import geotrellis.spark._
import protos.keyMessages._


trait SpaceTimeKeyProtoBuf {
  implicit def spaceTimeKeyProtoBufCodec = new ProtoBufCodec[SpaceTimeKey, ProtoSpaceTimeKey] {
    def encode(spaceTimeKey: SpaceTimeKey): ProtoSpaceTimeKey =
      ProtoSpaceTimeKey(col = spaceTimeKey.col, row = spaceTimeKey.row, instant = spaceTimeKey.instant)

    def decode(message: ProtoSpaceTimeKey): SpaceTimeKey =
      SpaceTimeKey(message.col, message.row, message.instant)
  }
}
