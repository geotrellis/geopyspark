from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from py4j.java_gateway import java_import
from geopyspark.avroserializer import AvroSerializer
from geopyspark.tests.base_test_class import BaseTestClass

import unittest


class ExtentSchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.ExtentWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    ew = BaseTestClass.geopysc._jvm.ExtentWrapper

    tup = ew.testOut(BaseTestClass.geopysc.sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2())

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_extents(self):
        encoded = self.rdd.map(lambda s: s)
        actual_encoded = encoded.collect()

        expected_encoded = [
            {"xmin": 0.0, "ymin": 0.0, "xmax": 1.0, "ymax": 1.0},
            {"xmin": 1.0, "ymin": 2.0, "xmax": 3.0, "ymax": 4.0},
            {"xmin": 5.0, "ymin": 6.0, "xmax": 7.0, "ymax": 8.0}
        ]

        for actual, expected in zip(actual_encoded, expected_encoded):
            assert(actual == expected)

    def test_decoded_extents(self):
        expected_extents = [
            {'xmin': 0, 'ymin': 0, 'xmax': 1, 'ymax': 1},
            {'xmin': 1, 'ymin': 2, 'xmax': 3, 'ymax': 4},
            {'xmin': 5, 'ymin': 6, 'xmax': 7, 'ymax': 8}
        ]

        for actual, expected in zip(self.collected, expected_extents):
            self.assertDictEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
