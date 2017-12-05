package geopyspark.translator.protobufs

import geopyspark.translator.ProtoBufCodec

import geopyspark.translator._
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
