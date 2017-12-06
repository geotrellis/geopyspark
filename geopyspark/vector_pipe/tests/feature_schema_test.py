import unittest
import pytest
from shapely.geometry import Point, LineString, MultiLineString
from dateutil import parser

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.vector_pipe import Feature, Properties
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.vector_pipe.vector_pipe_protobufcodecs import (feature_decoder, to_pb_feature, feature_encoder)
from geopyspark.tests.base_test_class import BaseTestClass


class FeatureSchemaTest(BaseTestClass):
    sc = BaseTestClass.pysc._jsc.sc()
    fw = BaseTestClass.pysc._jvm.geopyspark.vectorpipe.tests.schemas.FeatureWrapper

    java_rdd = fw.testOut(sc)
    ser = ProtoBufSerializer(feature_decoder, None)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))

    metadata = Properties(
        element_id=1993,
        user="Jake",
        uid=19144,
        changeset=10,
        version=24,
        minor_version=5,
        timestamp=parser.parse("2012-06-05T07:00:00UTC"),
        visible=True,
        tags={'amenity': 'embassy', 'diplomatic': 'embassy', 'country': 'azavea'}
    )

    point = Point(0, 2)
    line_1 = LineString([point, Point(1, 3), Point(2, 4), Point(3, 5), Point(4, 6)])
    line_2 = LineString([Point(5, 7), Point(6, 8), Point(7, 9), Point(8, 10), Point(9, 11)])
    multi_line = MultiLineString([line_1, line_2])

    features = [
        Feature(point, metadata),
        Feature(line_1, metadata),
        Feature(multi_line, metadata)
    ]

    collected = [f for f in rdd.collect()]

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_decoder(self):
        geoms = [g.geometry for g in self.collected]
        ms = [m.properties for m in self.collected]

        for x in self.features:
            self.assertTrue(x.geometry in geoms)
            self.assertTrue(x.properties in ms)

    def test_encoder(self):
        expected_encoded = [to_pb_feature(f).SerializeToString() for f in self.features]
        actual_encoded = [feature_encoder(f) for f in self.collected]

        for x in expected_encoded:
            self.assertTrue(x in actual_encoded)


if __name__ == "__main__":
    unittest.main()
