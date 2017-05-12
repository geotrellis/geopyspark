import os
import unittest
import numpy as np

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.avroserializer import AvroSerializer
from geopyspark.avroregistry import AvroRegistry
from geopyspark.tests.base_test_class import BaseTestClass


def decoder(x):
    tup_decoder = AvroRegistry.tuple_decoder

    tuples = x['pairs']
    return [tup_decoder(tup) for tup in tuples]

def encoder(xs):
    tup_encoder = AvroRegistry.tuple_encoder
    return {'pairs': [tup_encoder(x) for x in xs]}


class KeyValueRecordSchemaTest(unittest.TestCase):
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

    ew = BaseTestClass.geopysc._jvm.geopyspark.geotrellis.tests.schemas.KeyValueRecordWrapper

    tup = ew.testOut(BaseTestClass.geopysc.sc)
    java_rdd = tup._1()

    ser = AvroSerializer(tup._2(), decoder, encoder)
    rdd = RDD(java_rdd, BaseTestClass.geopysc.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_kvs(self):
        encoded = self.rdd.map(lambda s: encoder(s))
        actual_kvs = encoded.collect()

        encoded_tiles = [
            {'bands':
             [{'cells': bytearray([0, 1, 2, 3, 4, 5]), 'rows': 3, 'cols': 2, 'noDataValue': -128}]
            },
            {'bands':
             [{'cells': bytearray([0, 1, 2, 3, 4, 5]), 'rows': 2, 'cols': 3, 'noDataValue': -128}]
            },
            {'bands':
             [{'cells': bytearray([0, 1, 2, 3, 4, 5]), 'rows': 6, 'cols': 1, 'noDataValue': -128}]
            }
        ]
        encoded_tuples = [
            {'_1': encoded_tiles[0], '_2': self.extents[0]},
            {'_1': encoded_tiles[1], '_2': self.extents[1]},
            {'_1': encoded_tiles[2], '_2': self.extents[2]}
        ]

        expected_kvs = [
            {'pairs': encoded_tuples},
            {'pairs': encoded_tuples},
        ]

        for actual, expected in zip(actual_kvs, expected_kvs):
            actual_pairs = actual['pairs']
            expected_pairs = expected['pairs']

            for a, e in zip(actual_pairs, expected_pairs):
                self.assertDictEqual(a['_2'], e['_2'])

    def test_decoded_kvs(self):
        expected_kvs = [self.tuple_list, self.tuple_list]

        for actual_tuples, expected_tuples in zip(self.collected, expected_kvs):
            for actual, expected in zip(actual_tuples, expected_tuples):
                (actual_tile, actual_extent) = actual
                (expected_tile, expected_extent) = expected

                self.assertDictEqual(actual_extent, expected_extent)


if __name__ == "__main__":
    unittest.main()
