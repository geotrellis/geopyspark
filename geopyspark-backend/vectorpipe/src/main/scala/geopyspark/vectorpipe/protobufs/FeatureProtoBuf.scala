package geopyspark.vectorpipe.protobufs

import geopyspark.util._
import geotrellis.vector._
import geotrellis.vector.io.wkb.WKB

import vectorpipe.osm._

import protos.featureMessages._

import java.time.ZonedDateTime

import com.google.protobuf.ByteString


trait FeatureProtoBuf {
  implicit def featureProtoBufCodec = new ProtoBufCodec[Feature[Geometry, ElementMeta], ProtoFeature] {
    def encode(feature: Feature[Geometry, ElementMeta]): ProtoFeature = {
      val geom = feature.geom
      val data = feature.data

      val geomBytes: ByteString = ByteString.copyFrom(WKB.write(geom))
      val tags: Array[ProtoTag] = data.tags.map { case (k, v) => ProtoTag(key = k, value = v) }.toArray
      val protoTags: ProtoTags = ProtoTags(tags = tags)
      val protoMetadata: ProtoMetadata =
        ProtoMetadata(
          id = data.id,
          user = data.user,
          uid = data.uid,
          changeset = data.changeset,
          version = data.version,
          minorVersion = data.minorVersion,
          timestamp = data.timestamp.toString,
          visible = data.visible,
          tags = Some(protoTags))

      ProtoFeature(geom = geomBytes, metadata = Some(protoMetadata))
    }

    def decode(message: ProtoFeature): Feature[Geometry, ElementMeta] = {
      val geomBytes: Array[Byte] = message.geom.toByteArray
      val metadata = message.metadata.get

      val protoTags: ProtoTags = metadata.tags.get
      val tags: Map[String, String] = protoTags.tags.map { tag => (tag.key -> tag.value) }.toMap
      val elemMeta: ElementMeta =
        ElementMeta(
          id = metadata.id,
          user = metadata.user,
          uid = metadata.uid,
          changeset = metadata.changeset,
          version = metadata.version,
          minorVersion = metadata.minorVersion,
          timestamp = ZonedDateTime.parse(metadata.timestamp).toInstant,
          visible = metadata.visible,
          tags = tags)

      Feature(WKB.read(geomBytes), elemMeta)
    }
  }
}
