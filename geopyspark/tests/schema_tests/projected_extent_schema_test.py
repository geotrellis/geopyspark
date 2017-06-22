import unittest
import pytest

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.geotrellis import Extent, ProjectedExtent
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.geotrellis.protobufcodecs import (projected_extent_decoder,
                                                  projected_extent_encoder,
                                                  to_pb_projected_extent)
from geopyspark.tests.base_test_class import BaseTestClass


class ProjectedExtentSchemaTest(BaseTestClass):
    projected_extents = [
        {'epsg': 2004, 'extent': {'xmax': 1.0, 'xmin': 0.0, 'ymax': 1.0, 'ymin': 0.0}, 'proj4': None},
        {'epsg': 2004, 'extent': {'xmax': 3.0, 'xmin': 1.0, 'ymax': 4.0, 'ymin': 2.0}, 'proj4': None},
        {'epsg': 2004, 'extent': {'xmax': 7.0, 'xmin': 5.0, 'ymax': 8.0, 'ymin': 6.0}, 'proj4': None}]

    sc = BaseTestClass.pysc._jsc.sc()
    ew = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.ProjectedExtentWrapper

    java_rdd = ew.testOut(sc)
    ser = ProtoBufSerializer(projected_extent_decoder,
                             projected_extent_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = [pex._asdict() for pex in rdd.collect()]

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def result_checker(self, actual_pe, expected_pe):
        for actual, expected in zip(actual_pe, expected_pe):
            self.assertDictEqual(actual, expected)

    def test_encoded_pextents(self):
        actual_encoded = [projected_extent_encoder(x) for x in self.rdd.collect()]

        for x in range(0, len(self.projected_extents)):
            self.projected_extents[x]['extent'] = Extent(**self.projected_extents[x]['extent'])

        expected_encoded = [
            to_pb_projected_extent(ProjectedExtent(**ex)).SerializeToString() for ex in self.projected_extents
        ]

        for actual, expected in zip(actual_encoded, expected_encoded):
            self.assertEqual(actual, expected)

    def test_decoded_pextents(self):
        self.result_checker(self.collected, self.projected_extents)


if __name__ == "__main__":
    unittest.main()
