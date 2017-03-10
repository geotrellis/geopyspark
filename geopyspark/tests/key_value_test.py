from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from py4j.java_gateway import java_import
from geopyspark.avroserializer import AvroSerializer
from geopyspark.avroregistry import AvroRegistry
from geopyspark.tests.base_test_class import BaseTestClass

import numpy as np
import unittest
import pytest
import os


def decoder(x):
    tup_decoder = AvroRegistry.tuple_decoder
    tile_decoder = AvroRegistry.tile_decoder

    tuples = x['pairs']
    return [tup_decoder(tup, key_decoder=tile_decoder) for tup in tuples]

def encoder(xs):
    tup_encoder = AvroRegistry.tuple_encoder
    tile_encoder = AvroRegistry.tile_encoder
    return {'pairs': [tup_encoder(x, key_encoder=tile_encoder) for x in xs]}


class KeyValueRecordSchemaTest(unittest.TestCase):
    path = "geopyspark.geotrellis.tests.schemas.KeyValueRecordWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    extents = [
        {'xmin': 0, 'ymin': 0, 'xmax': 1, 'ymax': 1},
        {'xmin': 1, 'ymin': 2, 'xmax': 3, 'ymax': 4},
        {'xmin': 5, 'ymin': 6, 'xmax': 7, 'ymax': 8}
    ]

    arrs = [
        {'data': np.array(bytearray([0, 1, 2, 3, 4, 5])).reshape(3, 2), 'no_data_value': -128},
        {'data': np.array(bytearray([0, 1, 2, 3, 4, 5])).reshape(2, 3), 'no_data_value': -128},
        {'data': np.array(bytearray([0, 1, 2, 3, 4, 5])).reshape(6, 1), 'no_data_value': -128}
    ]

    tuple_list= [
        (arrs[0], extents[0]),
        (arrs[1], extents[1]),
        (arrs[2], extents[2])
    ]

    ew = BaseTestClass.geopysc._jvm.KeyValueRecordWrapper

    tup = ew.testOut(BaseTestClass.geopysc.sc)
    java_rdd = tup._1()

    ser = AvroSerializer(tup._2(), decoder, encoder)
    rdd = RDD(java_rdd, BaseTestClass.geopysc.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    @pytest.mark.skipif('TRAVIS' in os.environ, reason="Encoding using methods in Main cuases issues on Travis")
    def test_encoded_kvs(self):
        encoded = self.rdd.map(lambda s: encoder(s))
        actual_kvs = encoded.collect()

        encoded_tuples = [
            {'_1': AvroRegistry.tile_encoder(self.arrs[0]), '_2': self.extents[0]},
            {'_1': AvroRegistry.tile_encoder(self.arrs[1]), '_2': self.extents[1]},
            {'_1': AvroRegistry.tile_encoder(self.arrs[2]), '_2': self.extents[2]}
        ]

        expected_kvs = [
            {'pairs': encoded_tuples},
            {'pairs': encoded_tuples},
        ]

        for actual, expected in zip(actual_kvs, expected_kvs):
            actual_pairs = actual['pairs']
            expected_pairs = expected['pairs']

            for a, e in zip(actual_pairs, expected_pairs):
                self.assertDictEqual(a, e)

    def test_decoded_kvs(self):
        expected_kvs = [self.tuple_list, self.tuple_list]

        for actual_tuples, expected_tuples in zip(self.collected, expected_kvs):
            for actual, expected in zip(actual_tuples, expected_tuples):
                (actual_tile, actual_extent) = actual
                (expected_tile, expected_extent) = expected

                self.assertTrue((actual_tile['data'] == expected_tile['data']).all())
                self.assertDictEqual(actual_extent, expected_extent)


if __name__ == "__main__":
    unittest.main()
