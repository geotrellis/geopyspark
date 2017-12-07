import datetime
from shapely.wkb import loads, dumps
from dateutil import parser

from geopyspark.geopyspark_utils import ensure_pyspark
ensure_pyspark()

from geopyspark.vector_pipe.protobuf.featureMessages_pb2 import (ProtoFeature,
                                                                 ProtoMetadata,
                                                                 ProtoTags,
                                                                 ProtoTag)
from geopyspark.vector_pipe import Feature, Properties


def from_pb_tags(pb_tags):
    return {tags.key: tags.value for tags in pb_tags.tags}

def from_pb_properties(pb_metadata):
    time = parser.parse(pb_metadata.timestamp)
    tags = from_pb_tags(pb_metadata.tags)

    return Properties(
        element_id=pb_metadata.id,
        user=pb_metadata.user,
        uid=pb_metadata.uid,
        changeset=pb_metadata.changeset,
        version=pb_metadata.version,
        minor_version=pb_metadata.minorVersion,
        timestamp=time,
        visible=pb_metadata.visible,
        tags=tags)

def feature_decoder(proto_bytes):
    pb_feature = ProtoFeature.FromString(proto_bytes)

    return from_pb_feature(pb_feature)

def from_pb_feature(pb_feature):
    metadata = from_pb_properties(pb_feature.metadata)
    geometry = loads(pb_feature.geom)

    return Feature(geometry=geometry, properties=metadata)

def to_pb_properties(metadata):
    pb_tags = ProtoTags(tags=[ProtoTag(key=k, value=v) for k, v in metadata.tags.items()])

    return ProtoMetadata(
        id=metadata.element_id,
        user=metadata.user,
        uid=metadata.uid,
        changeset=metadata.changeset,
        version=metadata.version,
        minorVersion=metadata.minor_version,
        timestamp=str(metadata.timestamp),
        visible=metadata.visible,
        tags=pb_tags)

def to_pb_feature(feature):
    geom_bytes = dumps(feature.geometry)
    pb_properties = to_pb_properties(feature.properties)

    return ProtoFeature(geom=geom_bytes, metadata=pb_properties)

def feature_encoder(feature):
    return to_pb_feature(feature).SerializeToString()
