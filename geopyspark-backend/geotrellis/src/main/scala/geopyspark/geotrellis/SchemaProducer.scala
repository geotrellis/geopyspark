package geopyspark.geotrellis

import geotrellis.vector._
import geotrellis.raster._
import geotrellis.spark._
import geotrellis.spark.io.avro._


object SchemaProducer {
  def getSchema(keyType: String, valueType: String): String =
    (keyType, valueType) match {
      case ("ProjectedExtent", "Tile") =>
        implicitly[AvroRecordCodec[(ProjectedExtent, Tile)]].schema.toString
      case ("ProjectedExtent", "MultibandTile") =>
        implicitly[AvroRecordCodec[(ProjectedExtent, MultibandTile)]].schema.toString
      case ("TemporalProjectedExtent", "Tile") =>
        implicitly[AvroRecordCodec[(TemporalProjectedExtent, Tile)]].schema.toString
      case ("TemporalProjectedExtent", "MultibandTile") =>
        implicitly[AvroRecordCodec[(TemporalProjectedExtent, MultibandTile)]].schema.toString

      case ("SpatialKey", "Tile") =>
        implicitly[AvroRecordCodec[(SpatialKey, Tile)]].schema.toString
      case ("SpatialKey", "MultibandTile") =>
        implicitly[AvroRecordCodec[(SpatialKey, MultibandTile)]].schema.toString
      case ("SpaceTimeKey", "Tile") =>
        implicitly[AvroRecordCodec[(SpaceTimeKey, Tile)]].schema.toString
      case ("SpaceTimeKey", "MultibandTile") =>
        implicitly[AvroRecordCodec[(SpaceTimeKey, MultibandTile)]].schema.toString
    }
}
