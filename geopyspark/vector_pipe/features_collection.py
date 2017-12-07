from json import loads
from geopyspark import create_python_rdd
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.vector_pipe.vector_pipe_protobufcodecs import feature_decoder, feature_encoder


class FeaturesCollection(object):
    def __init__(self, scala_features):
        self.scala_features = scala_features

    def get_point_features_rdd(self):

        return self._get_rdd(self.scala_features.toProtoPoints())

    def get_line_features_rdd(self):

        return self._get_rdd(self.scala_features.toProtoLines())

    def get_polygon_features_rdd(self):

        return self._get_rdd(self.scala_features.toProtoPolygons())

    def get_multipolygon_features_rdd(self):

        return self._get_rdd(self.scala_features.toProtoMultiPolygons())

    def _get_rdd(self, jrdd):
        ser = ProtoBufSerializer(feature_decoder, feature_encoder)

        return create_python_rdd(jrdd, ser)

    def get_point_tags(self):
        return loads(self.scala_features.getPointTags())

    def get_line_tags(self):
        return loads(self.scala_features.getLineTags())

    def get_polygon_tags(self):
        return loads(self.scala_features.getPolygonTags())

    def get_multipolygon_tags(self):
        return loads(self.scala_features.getMultiPolygonTags())
