from json import loads
from geopyspark import create_python_rdd
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.vector_pipe.vector_pipe_protobufcodecs import feature_decoder, feature_encoder


class FeaturesCollection(object):
    """Represents a collection of features from OSM data. A ``feature`` is
    a geometry that is derived from an OSM Element with that Element's associated metadata.
    These ``feature``\s are grouped together by their geometry type.

    There are 4 different types of geometries that a ``feature`` can contain:
        - ``Point``\s
        - ``Line``\s
        - ``Polygon``\s
        - ``MultiPolygon``\s

    Args:
        scala_features (py4j.JavaObject): The Scala representation of ``FeaturesCollection``.

    Attributes:
        scala_features (py4j.JavaObject): The Scala representation of ``FeaturesCollection``.
    """

    def __init__(self, scala_features):
        self.scala_features = scala_features

    def get_point_features_rdd(self):
        """Returns each ``Point`` ``feature`` in the ``FeaturesCollection``
        as a :class:`~geopyspark.vector_pipe.Feature` in a Python RDD.

        Returns:
            ``RDD[Feature]``
        """

        return self._get_rdd(self.scala_features.toProtoPoints())

    def get_line_features_rdd(self):
        """Returns each ``Line`` ``feature`` in the ``FeaturesCollection``
        as a :class:`~geopyspark.vector_pipe.Feature` in a Python RDD.

        Returns:
            ``RDD[Feature]``
        """

        return self._get_rdd(self.scala_features.toProtoLines())

    def get_polygon_features_rdd(self):
        """Returns each ``Polygon`` ``feature`` in the ``FeaturesCollection``
        as a :class:`~geopyspark.vector_pipe.Feature` in a Python RDD.

        Returns:
            ``RDD[Feature]``
        """

        return self._get_rdd(self.scala_features.toProtoPolygons())

    def get_multipolygon_features_rdd(self):
        """Returns each ``MultiPolygon`` ``feature`` in the ``FeaturesCollection``
        as a :class:`~geopyspark.vector_pipe.Feature` in a Python RDD.

        Returns:
            ``RDD[Feature]``
        """

        return self._get_rdd(self.scala_features.toProtoMultiPolygons())

    def _get_rdd(self, jrdd):
        ser = ProtoBufSerializer(feature_decoder, feature_encoder)

        return create_python_rdd(jrdd, ser)

    def get_point_tags(self):
        """Returns all of the unique tags for all of the ``Point``\s in the
        ``FeaturesCollection`` as a ``dict``. Both the keys and values of the
        ``dict`` will be ``str``\s.

        Returns:
            dict
        """

        return loads(self.scala_features.getPointTags())

    def get_line_tags(self):
        """Returns all of the unique tags for all of the ``Line``\s in the
        ``FeaturesCollection`` as a ``dict``. Both the keys and values of the
        ``dict`` will be ``str``\s.

        Returns:
            dict
        """

        return loads(self.scala_features.getLineTags())

    def get_polygon_tags(self):
        """Returns all of the unique tags for all of the ``Polygon``\s in the
        ``FeaturesCollection`` as a ``dict``. Both the keys and values of the
        ``dict`` will be ``str``\s.

        Returns:
            dict
        """

        return loads(self.scala_features.getPolygonTags())

    def get_multipolygon_tags(self):
        """Returns all of the unique tags for all of the ``MultiPolygon``\s in the
        ``FeaturesCollection`` as a ``dict``. Both the keys and values of the
        ``dict`` will be ``str``\s.

        Returns:
            dict
        """

        return loads(self.scala_features.getMultiPolygonTags())
