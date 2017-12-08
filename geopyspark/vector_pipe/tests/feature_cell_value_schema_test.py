import unittest
import pytest
from shapely.geometry import Point, LineString, MultiLineString

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.vector_pipe import Feature, CellValue
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.vector_pipe.vector_pipe_protobufcodecs import (feature_cellvalue_decoder,
                                                               to_pb_feature_cellvalue,
                                                               feature_cellvalue_encoder)
from geopyspark.tests.base_test_class import BaseTestClass


class FeatureCellValueSchemaTest(BaseTestClass):
    sc = BaseTestClass.pysc._jsc.sc()
    fw = BaseTestClass.pysc._jvm.geopyspark.vectorpipe.tests.schemas.FeatureCellValueWrapper

    java_rdd = fw.testOut(sc)
    ser = ProtoBufSerializer(feature_cellvalue_decoder, feature_cellvalue_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))

    point = Point(0, 2)
    line_1 = LineString([point, Point(1, 3), Point(2, 4), Point(3, 5), Point(4, 6)])
    line_2 = LineString([Point(5, 7), Point(6, 8), Point(7, 9), Point(8, 10), Point(9, 11)])
    multi_line = MultiLineString([line_1, line_2])

    features = [
        Feature(point, CellValue(2, 1)),
        Feature(line_1, CellValue(1, 0)),
        Feature(multi_line, CellValue(1, 0))
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
        expected_encoded = [to_pb_feature_cellvalue(f).SerializeToString() for f in self.features]
        actual_encoded = [feature_cellvalue_encoder(f) for f in self.collected]

        for x in expected_encoded:
            self.assertTrue(x in actual_encoded)


if __name__ == "__main__":
    unittest.main()
