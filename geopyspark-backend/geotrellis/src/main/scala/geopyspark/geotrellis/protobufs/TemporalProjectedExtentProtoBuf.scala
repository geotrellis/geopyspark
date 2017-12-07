package geopyspark.geotrellis.protobufs

import geopyspark.geotrellis._
import geopyspark.util.ProtoBufCodec
import geotrellis.spark._

import protos.extentMessages._


trait TemporalProjectedExtentProtoBuf {
  implicit def temporalProjectedExtentProtoBufCodec = new ProtoBufCodec[TemporalProjectedExtent, ProtoTemporalProjectedExtent] {
    def encode(extent: TemporalProjectedExtent): ProtoTemporalProjectedExtent =
      ProtoTemporalProjectedExtent(
        extent = Some(extentProtoBufCodec.encode(extent.extent)),
        crs = Some(crsProtoBufCodec.encode(extent.crs)),
        instant = extent.instant
      )

    def decode(message: ProtoTemporalProjectedExtent): TemporalProjectedExtent =
      TemporalProjectedExtent(
        extentProtoBufCodec.decode(message.extent.get),
        crsProtoBufCodec.decode(message.crs.get),
        message.instant
      )
  }
}
