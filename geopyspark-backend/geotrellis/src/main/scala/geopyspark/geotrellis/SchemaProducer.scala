package geopyspark.geotrellis

import geotrellis.vector._
import geotrellis.raster._
import geotrellis.spark._
import geotrellis.spark.io.avro._


object SchemaProducer {
  def getSchema(keyType: String, valueType: String): String =
    (keyType, valueType) match {
      case ("ProjectedExtent", "Singleband") =>
        implicitly[AvroRecordCodec[(ProjectedExtent, Tile)]].schema.toString
      case ("ProjectedExtent", "Multiband") =>
        implicitly[AvroRecordCodec[(ProjectedExtent, MultibandTile)]].schema.toString
      case ("TemporalProjectedExtent", "Singleband") =>
        implicitly[AvroRecordCodec[(TemporalProjectedExtent, Tile)]].schema.toString
      case ("TemporalProjectedExtent", "Multiband") =>
        implicitly[AvroRecordCodec[(TemporalProjectedExtent, MultibandTile)]].schema.toString

      case ("SpatialKey", "Singleband") =>
        implicitly[AvroRecordCodec[(SpatialKey, Tile)]].schema.toString
      case ("SpatialKey", "Multiband") =>
        implicitly[AvroRecordCodec[(SpatialKey, MultibandTile)]].schema.toString
      case ("SpaceTimeKey", "Singleband") =>
        implicitly[AvroRecordCodec[(SpaceTimeKey, Tile)]].schema.toString
      case ("SpaceTimeKey", "Multiband") =>
        implicitly[AvroRecordCodec[(SpaceTimeKey, MultibandTile)]].schema.toString
    }
}
