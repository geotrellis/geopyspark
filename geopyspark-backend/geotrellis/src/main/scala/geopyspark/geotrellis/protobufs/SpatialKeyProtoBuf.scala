package geopyspark.geotrellis.protobufs

import geopyspark.util._
import geopyspark.geotrellis._
import geotrellis.spark._
import protos.keyMessages._


trait SpatialKeyProtoBuf {
  implicit def spatialKeyProtoBufCodec = new ProtoBufCodec[SpatialKey, ProtoSpatialKey] {
    def encode(spatialKey: SpatialKey): ProtoSpatialKey =
      ProtoSpatialKey(col = spatialKey.col, row = spatialKey.row)

    def decode(message: ProtoSpatialKey): SpatialKey =
      SpatialKey(message.col, message.row)
  }
}
