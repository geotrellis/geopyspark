package geopyspark.geotrellis.protobufs

import geopyspark.util.ProtoBufCodec
import geotrellis.vector._
import protos.extentMessages._


trait ExtentProtoBuf {
  implicit def extentProtoBufCodec = new ProtoBufCodec[Extent, ProtoExtent] {
    def encode(extent: Extent): ProtoExtent =
      ProtoExtent(
        xmin = extent.xmin,
        ymin = extent.ymin,
        xmax = extent.xmax,
        ymax = extent.ymax)

    def decode(message: ProtoExtent): Extent =
      Extent(message.xmin, message.ymin, message.xmax, message.ymax)
  }
}
