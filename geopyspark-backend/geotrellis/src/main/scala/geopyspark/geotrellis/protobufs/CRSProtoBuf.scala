package geopyspark.geotrellis.protobufs

import protos.extentMessages._
import geopyspark.util.ProtoBufCodec
import geotrellis.proj4._


trait CRSProtoBuf {
  implicit def crsProtoBufCodec = new ProtoBufCodec[CRS, ProtoCRS] {
    override def encode(thing: CRS): ProtoCRS =
      if (thing.epsgCode.isDefined)
        ProtoCRS(epsg = thing.epsgCode.get)
      else
        ProtoCRS(proj4 = thing.toProj4String)

    override def decode(message: ProtoCRS): CRS =
      message.epsg match {
        case 0 => CRS.fromString(message.proj4)
        case epsg => CRS.fromEpsgCode(epsg)
      }
  }
}
