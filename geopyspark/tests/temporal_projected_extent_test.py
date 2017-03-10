from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from py4j.java_gateway import java_import
from geopyspark.avroserializer import AvroSerializer
from geopyspark.tests.base_test_class import BaseTestClass

import unittest


class TemporalProjectedExtentSchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.TemporalProjectedExtentWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    expected_tpextents = [
        {'instant': 0, 'epsg': 2004, 'extent': {'xmin': 0, 'ymin': 0, 'xmax': 1, 'ymax': 1}},
        {'instant': 1, 'epsg': 2004, 'extent': {'xmin': 1, 'ymin': 2, 'xmax': 3, 'ymax': 4}},
        {'instant': 2, 'epsg': 2004, 'extent': {'xmin': 5, 'ymin': 6, 'xmax': 7, 'ymax': 8}},
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    ew = BaseTestClass.pysc._gateway.jvm.TemporalProjectedExtentWrapper

    tup = ew.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2())

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tpextents(self):
        encoded = self.rdd.map(lambda s: s)
        actual_encoded = encoded.collect()

        for actual, expected in zip(actual_encoded, self.expected_tpextents):
            self.assertEqual(actual, expected)

    def test_decoded_tpextents(self):
        for actual, expected in zip(self.collected, self.expected_tpextents):
            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
