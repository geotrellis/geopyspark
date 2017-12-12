import datetime
from shapely.wkb import loads, dumps
from dateutil import parser

from geopyspark.geopyspark_utils import ensure_pyspark
ensure_pyspark()

from geopyspark.vector_pipe.protobuf.featureMessages_pb2 import (ProtoFeature,
                                                                 ProtoFeatureCellValue,
                                                                 ProtoMetadata,
                                                                 ProtoTags,
                                                                 ProtoTag,
                                                                 ProtoCellValue)
from geopyspark.vector_pipe import Feature, Properties, CellValue


# Decoders

def from_pb_tags(pb_tags):
    """Creates a ``dict`` from ``ProtoTags``.

    Args:
        pb_tags (ProtoTags): The ``ProtoTags`` instance to be converted.

    Returns:
        dict
    """

    if list(pb_tags.tags):
        return {tags.key: tags.value for tags in pb_tags.tags}
    else:
        return {}

def from_pb_properties(pb_metadata):
    """Creates ``Properties`` from ``ProtoMetadata``.

    Args:
        pb_metadata (ProtoMetadata): The ``ProtoMetadata`` instance to be converted.

    Returns:
        :class:`~geopyspark.vector_pipe.Properties`
    """

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

def from_pb_feature_cellvalue(pb_feature_cellvalue):
    """Creates a ``Feature`` with ``properties`` of ``CellValue``
    from ``ProtoFeature``.

    Args:
        pb_feature_cellvalue (ProtoFeatureCellValue): The ``ProtoFeatureCellValue`` instance
            to be converted.

    Returns:
        :class:`~geopyspark.vector_pipe.Feature`
    """

    geometry = loads(pb_feature_cellvalue.geom)
    cellvalue = CellValue(pb_feature_cellvalue.cellValue.value,
                          pb_feature_cellvalue.cellValue.zindex)

    return Feature(geometry, cellvalue)

def from_pb_feature(pb_feature):
    """Creates a ``Feature`` with ``properties`` of ``Properties``
    from ``ProtoFeature``.

    Args:
        pb_feature (ProtoFeature): The ``ProtoFeature`` instance to be converted.

    Returns:
        :class:`~geopyspark.vector_pipe.Feature`
    """

    metadata = from_pb_properties(pb_feature.metadata)
    geometry = loads(pb_feature.geom)

    return Feature(geometry=geometry, properties=metadata)

def feature_decoder(proto_bytes):
    """Deserializes the ``ProtoFeature`` bytes into Python.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.

    Returns:
        :class:`~geopyspark.vector_pipe.Feature`
    """

    pb_feature = ProtoFeature.FromString(proto_bytes)

    return from_pb_feature(pb_feature)

def feature_cellvalue_decoder(proto_bytes):
    """Deserializes the ``ProtoFeatureCellValue`` bytes into Python.

    Args:
        proto_bytes (bytes): The ProtoBuf encoded bytes of the ProtoBuf class.

    Returns:
        :class:`~geopyspark.vector_pipe.Feature`
    """

    pb_feature_cellvalue = ProtoFeatureCellValue.FromString(proto_bytes)

    return from_pb_feature_cellvalue(pb_feature_cellvalue)


# Encoders

def to_pb_properties(metadata):
    """Converts an instance of ``Properties`` to ``ProtoMetadata``.

    Args:
        obj (:class:`~geopyspark.vector_pipe.Properties`): An instance of ``Properties``.

    Returns:
        ProtoProperties
    """

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

def to_pb_cellvalue(cv):
    """Converts an instance of ``CellValue`` to ``ProtoCellValue``.

    Args:
        obj (:class:`~geopyspark.vector_pipe.CellValue`): An instance of ``CellValue``.

    Returns:
        ProtoCellValue
    """

    return ProtoCellValue(value=cv.value, zindex=cv.zindex)

def to_pb_feature(feature):
    """Converts an instance of ``Feature`` with ``properties`` of ``Properties`` to
    ``ProtoFeature``.

    Args:
        feature (:class:`~geopyspark.vector_pipe.Feature`): An instance of ``Feature`` to be
            encoded.

    Returns:
       ProtoFeature
    """

    geom_bytes = dumps(feature.geometry)
    pb_properties = to_pb_properties(feature.properties)

    return ProtoFeature(geom=geom_bytes, metadata=pb_properties)

def to_pb_feature_cellvalue(feature):
    """Converts an instance of ``Feature`` with ``properties`` of ``CellValue`` to
    ``ProtoFeatureCellValue``.

    Args:
        feature (:class:`~geopyspark.vector_pipe.Feature`): An instance of ``Feature`` to be
            encoded.

    Returns:
       ProtoFeatureCellValue
    """

    geom_bytes = dumps(feature.geometry)
    cellvalue = to_pb_cellvalue(feature.properties)

    return ProtoFeatureCellValue(geom=geom_bytes, cellValue=cellvalue)

def feature_encoder(feature):
    """Encodes a ``Feature`` with ``properties`` of ``Properties`` into ``ProtoFeature`` bytes.

    Args:
        feature (:class:`~geopyspark.vector_pipe.Feature`): An instance of ``Feature`` to be
            encoded.

    Returns:
       bytes
    """

    return to_pb_feature(feature).SerializeToString()

def feature_cellvalue_encoder(feature):
    """Encodes a ``Feature`` with ``properties`` of ``CellValue`` into
    ``ProtoFeatureCellValue`` bytes.

    Args:
        feature (:class:`~geopyspark.vector_pipe.Feature`): An instance of ``Feature`` to be
            encoded.

    Returns:
       bytes
    """

    return to_pb_feature_cellvalue(feature).SerializeToString()
