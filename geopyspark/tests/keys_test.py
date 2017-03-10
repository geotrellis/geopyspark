from pyspark import SparkContext, RDD
from pyspark.serializers import AutoBatchedSerializer
from py4j.java_gateway import java_import
from geopyspark.avroserializer import AvroSerializer
from geopyspark.tests.base_test_class import BaseTestClass

import unittest


class SpatialKeySchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.SpatialKeyWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    expected_skey = {'col': 7, 'row': 3}

    sc = BaseTestClass.pysc._jsc.sc()
    ew = BaseTestClass.pysc._gateway.jvm.SpatialKeyWrapper

    tup = ew.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2())

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.first()

    def test_encoded_skeys(self):
        encoded = self.rdd.map(lambda s: s)
        actual_encoded = encoded.first()

        self.assertDictEqual(actual_encoded, self.expected_skey)

    def test_decoded_extents(self):
        self.assertDictEqual(self.collected, self.expected_skey)


class SpaceTimeKeySchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.SpaceTimeKeyWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    expected_skeys = [
        {'col': 7, 'row': 3, 'instant': 5},
        {'col': 9, 'row': 4, 'instant': 10},
        {'col': 11, 'row': 5, 'instant': 15}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    ew = BaseTestClass.pysc._gateway.jvm.SpaceTimeKeyWrapper

    tup = ew.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2())

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_skeys(self):
        encoded = self.rdd.map(lambda s: s)
        actual_encoded = encoded.collect()

        for actual, expected in zip(actual_encoded, self.expected_skeys):
            self.assertEqual(actual, expected)

    def test_decoded_extents(self):
        for actual, expected in zip(self.collected, self.expected_skeys):
            self.assertDictEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
