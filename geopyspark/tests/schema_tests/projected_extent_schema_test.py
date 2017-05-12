import unittest

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.avroserializer import AvroSerializer
from geopyspark.tests.base_test_class import BaseTestClass


class ProjectedExtentSchemaTest(BaseTestClass):
    projected_extents = [
        {'epsg': 2004, 'extent': {'xmax': 1.0, 'xmin': 0.0, 'ymax': 1.0, 'ymin': 0.0}, 'proj4': None},
        {'epsg': 2004, 'extent': {'xmax': 3.0, 'xmin': 1.0, 'ymax': 4.0, 'ymin': 2.0}, 'proj4': None},
        {'epsg': 2004, 'extent': {'xmax': 7.0, 'xmin': 5.0, 'ymax': 8.0, 'ymin': 6.0}, 'proj4': None}]

    sc = BaseTestClass.geopysc.pysc._jsc.sc()
    ew = BaseTestClass.geopysc.pysc._jvm.geopyspark.geotrellis.tests.schemas.ProjectedExtentWrapper

    tup = ew.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2())

    rdd = RDD(java_rdd, BaseTestClass.geopysc.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def result_checker(self, actual_pe, expected_pe):
        for actual, expected in zip(actual_pe, expected_pe):
            self.assertDictEqual(actual, expected)

    def test_encoded_pextents(self):
        encoded = self.rdd.map(lambda s: s)
        actual_encoded = encoded.collect()

        self.result_checker(actual_encoded, self.projected_extents)

    def test_decoded_pextents(self):
        self.result_checker(self.collected, self.projected_extents)


if __name__ == "__main__":
    unittest.main()
