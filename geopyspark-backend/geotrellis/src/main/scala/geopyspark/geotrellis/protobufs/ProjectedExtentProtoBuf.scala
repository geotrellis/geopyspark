package geopyspark.geotrellis.protobufs

import geopyspark.geotrellis._
import geopyspark.util.ProtoBufCodec
import geotrellis.vector._

import protos.extentMessages._


trait ProjectedExtentProtoBuf {
  implicit def projectedExtentProtoBufCodec = new ProtoBufCodec[ProjectedExtent, ProtoProjectedExtent] {
    def encode(extent: ProjectedExtent): ProtoProjectedExtent =
      ProtoProjectedExtent(
        extent = Some(extentProtoBufCodec.encode(extent.extent)),
        crs = Some(crsProtoBufCodec.encode(extent.crs))
      )

    def decode(message: ProtoProjectedExtent): ProjectedExtent =
      ProjectedExtent(
        extentProtoBufCodec.decode(message.extent.get),
        crsProtoBufCodec.decode(message.crs.get)
      )
  }
}
