import unittest

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from py4j.java_gateway import java_import
from geopyspark.avroserializer import AvroSerializer
from geopyspark.tests.base_test_class import BaseTestClass


class SpatialKeySchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.SpatialKeyWrapper"
    java_import(BaseTestClass.geopysc.pysc._gateway.jvm, path)

    expected_keys = {'col': 7, 'row': 3}

    sc = BaseTestClass.geopysc.pysc._jsc.sc()
    ew = BaseTestClass.geopysc.pysc._gateway.jvm.SpatialKeyWrapper

    tup = ew.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2())

    rdd = RDD(java_rdd, BaseTestClass.geopysc.pysc, AutoBatchedSerializer(ser))
    collected = rdd.first()

    def result_checker(self, actual_keys, expected_keys):
        self.assertDictEqual(actual_keys, expected_keys)

    def test_encoded_keyss(self):
        encoded = self.rdd.map(lambda s: s)
        actual_encoded = encoded.first()

        self.result_checker(actual_encoded, self.expected_keys)

    def test_decoded_extents(self):
        self.assertDictEqual(self.collected, self.expected_keys)


class SpaceTimeKeySchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.SpaceTimeKeyWrapper"
    java_import(BaseTestClass.geopysc.pysc._gateway.jvm, path)

    expected_keys = [
        {'col': 7, 'row': 3, 'instant': 5},
        {'col': 9, 'row': 4, 'instant': 10},
        {'col': 11, 'row': 5, 'instant': 15}
    ]

    sc = BaseTestClass.geopysc.pysc._jsc.sc()
    ew = BaseTestClass.geopysc.pysc._gateway.jvm.SpaceTimeKeyWrapper

    tup = ew.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2())

    rdd = RDD(java_rdd, BaseTestClass.geopysc.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def result_checker(self, actual_keys, expected_keys):
        for actual, expected in zip(actual_keys, expected_keys):
            self.assertDictEqual(actual, expected)

    def test_encoded_keyss(self):
        encoded = self.rdd.map(lambda s: s)
        actual_encoded = encoded.collect()

        self.result_checker(actual_encoded, self.expected_keys)

    def test_decoded_extents(self):
        self.result_checker(self.collected, self.expected_keys)


if __name__ == "__main__":
    unittest.main()
