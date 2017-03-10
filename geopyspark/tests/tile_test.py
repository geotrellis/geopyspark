from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from py4j.java_gateway import java_import
from geopyspark.avroserializer import AvroSerializer
from geopyspark.avroregistry import AvroRegistry
from geopyspark.tests.base_test_class import BaseTestClass

import numpy as np
import unittest


# TODO: CLEANUP THESE TESTS TO MAKE IT MORE DRY


class ShortTileSchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.ShortArrayTileWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    tiles = [
        {'data': np.array([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': -32768},
        {'data': np.array([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': -32768},
        {'data': np.array([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': -32768}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.ShortArrayTileWrapper

    tup = tw.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2(), AvroRegistry.tile_decoder, AvroRegistry.tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        encoded = self.rdd.map(lambda s: AvroRegistry.tile_encoder(s))
        actual_encoded = encoded.collect()

        expected_encoded = [
            {'cols': 2, 'rows': 2, 'cells': [0, 0, 1, 1], 'noDataValue': -32768},
            {'cols': 2, 'rows': 2, 'cells': [1, 2, 3, 4], 'noDataValue': -32768},
            {'cols': 2, 'rows': 2, 'cells': [5, 6, 7, 8], 'noDataValue': -32768}
        ]

        self.assertEqual(actual_encoded, expected_encoded)

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())


class UShortTileSchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.UShortArrayTileWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    tiles = [
        {'data': np.array([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': 0},
        {'data': np.array([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': 0},
        {'data': np.array([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': 0}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.UShortArrayTileWrapper

    tup = tw.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2(), AvroRegistry.tile_decoder, AvroRegistry.tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        encoded = self.rdd.map(lambda s: AvroRegistry.tile_encoder(s))
        actual_encoded = encoded.collect()

        expected_encoded = [
            {'cols': 2, 'rows': 2, 'cells': [0, 0, 1, 1], 'noDataValue': 0},
            {'cols': 2, 'rows': 2, 'cells': [1, 2, 3, 4], 'noDataValue': 0},
            {'cols': 2, 'rows': 2, 'cells': [5, 6, 7, 8], 'noDataValue': 0}
        ]

        self.assertEqual(actual_encoded, expected_encoded)

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())


class ByteTileSchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.ByteArrayTileWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    tiles = [
        {'data': np.array([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': -128},
        {'data': np.array([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': -128},
        {'data': np.array([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': -128}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.ByteArrayTileWrapper

    tup = tw.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2(), AvroRegistry.tile_decoder, AvroRegistry.tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        encoded = self.rdd.map(lambda s: AvroRegistry.tile_encoder(s))
        actual_encoded = encoded.collect()

        expected_encoded = [
            {'cols': 2, 'rows': 2, 'cells': bytearray([0, 0, 1, 1]), 'noDataValue': -128},
            {'cols': 2, 'rows': 2, 'cells': bytearray([1, 2, 3, 4]), 'noDataValue': -128},
            {'cols': 2, 'rows': 2, 'cells': bytearray([5, 6, 7, 8]), 'noDataValue': -128}
        ]

        self.assertEqual(actual_encoded, expected_encoded)

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())


class UByteTileSchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.UByteArrayTileWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    tiles = [
        {'data': np.array([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': -128},
        {'data': np.array([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': -128},
        {'data': np.array([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': -128}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.UByteArrayTileWrapper

    tup = tw.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2(), AvroRegistry.tile_decoder, AvroRegistry.tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        encoded = self.rdd.map(lambda s: AvroRegistry.tile_encoder(s))
        actual_encoded = encoded.collect()

        expected_encoded = [
            {'cols': 2, 'rows': 2, 'cells': bytearray([0, 0, 1, 1]), 'noDataValue': 0},
            {'cols': 2, 'rows': 2, 'cells': bytearray([1, 2, 3, 4]), 'noDataValue': 0},
            {'cols': 2, 'rows': 2, 'cells': bytearray([5, 6, 7, 8]), 'noDataValue': 0}
        ]

        self.assertEqual(actual_encoded, expected_encoded)

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())


class IntTileSchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.IntArrayTileWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    tiles = [
        {'data': np.array([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': -2147483648},
        {'data': np.array([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': -2147483648},
        {'data': np.array([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': -2147483648}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.IntArrayTileWrapper

    tup = tw.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2(), AvroRegistry.tile_decoder, AvroRegistry.tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        encoded = self.rdd.map(lambda s: AvroRegistry.tile_encoder(s))
        actual_encoded = encoded.collect()

        expected_encoded = [
            {'cols': 2, 'rows': 2, 'cells': [0, 0, 1, 1], 'noDataValue': -2147483648},
            {'cols': 2, 'rows': 2, 'cells': [1, 2, 3, 4], 'noDataValue': -2147483648},
            {'cols': 2, 'rows': 2, 'cells': [5, 6, 7, 8], 'noDataValue': -2147483648}
        ]

        self.assertEqual(actual_encoded, expected_encoded)

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())


class DoubleTileSchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.DoubleArrayTileWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    tiles = [
        {'data': np.array([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': True},
        {'data': np.array([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': True},
        {'data': np.array([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': True}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.DoubleArrayTileWrapper

    tup = tw.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2(), AvroRegistry.tile_decoder, AvroRegistry.tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        encoded = self.rdd.map(lambda s: AvroRegistry.tile_encoder(s))
        actual_encoded = encoded.collect()

        expected_encoded = [
            {'cols': 2, 'rows': 2, 'cells': [0, 0, 1, 1], 'noDataValue': True},
            {'cols': 2, 'rows': 2, 'cells': [1, 2, 3, 4], 'noDataValue': True},
            {'cols': 2, 'rows': 2, 'cells': [5, 6, 7, 8], 'noDataValue': True}
        ]

        self.assertEqual(actual_encoded, expected_encoded)

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())


class FloatTileSchemaTest(BaseTestClass):
    path = "geopyspark.geotrellis.tests.schemas.FloatArrayTileWrapper"
    java_import(BaseTestClass.pysc._gateway.jvm, path)

    tiles = [
        {'data': np.array([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': True},
        {'data': np.array([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': True},
        {'data': np.array([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': True}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.FloatArrayTileWrapper

    tup = tw.testOut(sc)
    java_rdd = tup._1()
    ser = AvroSerializer(tup._2(), AvroRegistry.tile_decoder, AvroRegistry.tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        encoded = self.rdd.map(lambda s: AvroRegistry.tile_encoder(s))
        actual_encoded = encoded.collect()

        expected_encoded = [
            {'cols': 2, 'rows': 2, 'cells': [0, 0, 1, 1], 'noDataValue': True},
            {'cols': 2, 'rows': 2, 'cells': [1, 2, 3, 4], 'noDataValue': True},
            {'cols': 2, 'rows': 2, 'cells': [5, 6, 7, 8], 'noDataValue': True}
        ]

        self.assertEqual(actual_encoded, expected_encoded)

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())


if __name__ == "__main__":
    unittest.main()
