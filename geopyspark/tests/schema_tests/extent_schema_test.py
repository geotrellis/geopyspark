import unittest
import pytest

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.geotrellis.protobufcodecs import (extent_decoder,
                                                   extent_encoder, to_pb_extent,
                                                   from_pb_extent)
from geopyspark.geotrellis import Extent
from geopyspark.tests.base_test_class import BaseTestClass


class ExtentSchemaTest(BaseTestClass):
    ew = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.ExtentWrapper
    java_rdd = ew.testOut(BaseTestClass.pysc._jsc.sc())
    ser = ProtoBufSerializer(extent_decoder, extent_encoder)
    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    expected_extents = [
        {"xmin": 0.0, "ymin": 0.0, "xmax": 1.0, "ymax": 1.0},
        {"xmin": 1.0, "ymin": 2.0, "xmax": 3.0, "ymax": 4.0},
        {"xmin": 5.0, "ymin": 6.0, "xmax": 7.0, "ymax": 8.0}
    ]

    @pytest.fixture(scope='class', autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def result_checker(self, actual_result, expected_result):
        for actual, expected in zip(actual_result, expected_result):
            self.assertDictEqual(actual, expected)

    def test_decoded_extents(self):
        actual_decoded = [from_pb_extent(ex)._asdict() for ex in self.collected]
        self.result_checker(actual_decoded, self.expected_extents)

    def test_encoded_extents(self):
        expected_encoded = [to_pb_extent(Extent(**x)).SerializeToString() for x in self.expected_extents]
        actual_encoded = [extent_encoder(x) for x in self.collected]
        for actual, expected in zip(actual_encoded, expected_encoded):
            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
    BaseTestClass.pysc.stop()
