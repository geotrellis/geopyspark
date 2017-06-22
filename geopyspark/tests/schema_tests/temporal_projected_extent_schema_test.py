import unittest
import pytest

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.geotrellis import Extent, TemporalProjectedExtent
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.geotrellis.protobufcodecs import (temporal_projected_extent_decoder,
                                                  temporal_projected_extent_encoder,
                                                  to_pb_temporal_projected_extent)
from geopyspark.tests.base_test_class import BaseTestClass


class TemporalProjectedExtentSchemaTest(BaseTestClass):
    expected_tpextents = [
        {'epsg': 2004, 'extent': {'xmax': 1.0, 'xmin': 0.0, 'ymax': 1.0, 'ymin': 0.0}, 'instant': 0, 'proj4': None},
        {'epsg': 2004, 'extent': {'xmax': 3.0, 'xmin': 1.0, 'ymax': 4.0, 'ymin': 2.0}, 'instant': 1, 'proj4': None},
        {'epsg': 2004, 'extent': {'xmax': 7.0, 'xmin': 5.0, 'ymax': 8.0, 'ymin': 6.0}, 'instant': 2, 'proj4': None}]

    sc = BaseTestClass.pysc._jsc.sc()
    ew = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.TemporalProjectedExtentWrapper

    java_rdd = ew.testOut(sc)
    ser = ProtoBufSerializer(temporal_projected_extent_decoder,
                             temporal_projected_extent_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = [tpex._asdict() for tpex in rdd.collect()]

    @pytest.fixture(scope='class', autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def result_checker(self, actual_tpe, expected_tpe):
        for actual, expected in zip(actual_tpe, expected_tpe):
            self.assertDictEqual(actual, expected)

    def test_encoded_tpextents(self):
        actual_encoded = [temporal_projected_extent_encoder(x) for x in self.rdd.collect()]

        for x in range(0, len(self.expected_tpextents)):
            self.expected_tpextents[x]['extent'] = Extent(**self.expected_tpextents[x]['extent'])

        expected_encoded = [
            to_pb_temporal_projected_extent(TemporalProjectedExtent(**ex)).SerializeToString() \
            for ex in self.expected_tpextents
        ]

        for actual, expected in zip(actual_encoded, expected_encoded):
            self.assertEqual(actual, expected)

    def test_decoded_tpextents(self):
        self.result_checker(self.collected, self.expected_tpextents)


if __name__ == "__main__":
    unittest.main()
