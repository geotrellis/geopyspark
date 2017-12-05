package geopyspark.translator.protobufs


object Implicits extends Implicits

trait Implicits extends CRSProtoBuf
    with ExtentProtoBuf
    with ProjectedExtentProtoBuf
    with TemporalProjectedExtentProtoBuf
    with SpatialKeyProtoBuf
    with SpaceTimeKeyProtoBuf
    with TileProtoBuf
    with MultibandTileProtoBuf
    with TupleProtoBuf
