import math
import unittest
import numpy as np

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.geotrellis.protobufcodecs import tile_decoder, tile_encoder, to_pb_tile
from geopyspark.tests.base_test_class import BaseTestClass


mapped_data_types = {
    'BIT': 0,
    'BYTE': 1,
    'UBYTE': 2,
    'SHORT': 3,
    'USHORT': 4,
    'INT': 5,
    'FLOAT': 6,
    'DOUBLE': 7
}


class ShortTileSchemaTest(BaseTestClass):
    tiles = [
        {'data': np.int16([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': -32768, 'data_type': 'SHORT'},
        {'data': np.int16([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': -32768, 'data_type': 'SHORT'},
        {'data': np.int16([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': -32768, 'data_type': 'SHORT'}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.ShortArrayTileWrapper

    java_rdd = tw.testOut(sc)
    ser = ProtoBufSerializer(tile_decoder, tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        expected_encoded = [to_pb_tile(x) for x in self.collected]

        for actual, expected in zip(self.tiles, expected_encoded):
            data = actual['data']
            rows, cols = data.shape

            self.assertEqual(expected.cols, cols)
            self.assertEqual(expected.rows, rows)
            self.assertEqual(expected.cellType.nd, actual['no_data_value'])
            self.assertEqual(expected.cellType.dataType, mapped_data_types[actual['data_type']])

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())
            self.assertTrue(actual['data'].dtype == expected['data'].dtype)
            self.assertEqual(actual['data'].shape, actual['data'].shape)


class UShortTileSchemaTest(BaseTestClass):
    tiles = [
        {'data': np.uint16([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': 0, 'data_type': 'USHORT'},
        {'data': np.uint16([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': 0, 'data_type': 'USHORT'},
        {'data': np.uint16([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': 0, 'data_type': 'USHORT'}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.UShortArrayTileWrapper

    java_rdd = tw.testOut(sc)
    ser = ProtoBufSerializer(tile_decoder, tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        expected_encoded = [to_pb_tile(x) for x in self.collected]

        for actual, expected in zip(self.tiles, expected_encoded):
            data = actual['data']
            rows, cols = data.shape

            self.assertEqual(expected.cols, cols)
            self.assertEqual(expected.rows, rows)
            self.assertEqual(expected.cellType.nd, actual['no_data_value'])
            self.assertEqual(expected.cellType.dataType, mapped_data_types[actual['data_type']])

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())
            self.assertTrue(actual['data'].dtype == expected['data'].dtype)
            self.assertEqual(actual['data'].shape, actual['data'].shape)


class ByteTileSchemaTest(BaseTestClass):
    tiles = [
        {'data': np.int8([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': -128, 'data_type': 'BYTE'},
        {'data': np.int8([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': -128, 'data_type': 'BYTE'},
        {'data': np.int8([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': -128, 'data_type': 'BYTE'}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.ByteArrayTileWrapper

    java_rdd = tw.testOut(sc)
    ser = ProtoBufSerializer(tile_decoder, tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        expected_encoded = [to_pb_tile(x) for x in self.collected]

        for actual, expected in zip(self.tiles, expected_encoded):
            data = actual['data']
            rows, cols = data.shape

            self.assertEqual(expected.cols, cols)
            self.assertEqual(expected.rows, rows)
            self.assertEqual(expected.cellType.nd, actual['no_data_value'])
            self.assertEqual(expected.cellType.dataType, mapped_data_types[actual['data_type']])

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())
            self.assertTrue(actual['data'].dtype == expected['data'].dtype)
            self.assertEqual(actual['data'].shape, actual['data'].shape)


class UByteTileSchemaTest(BaseTestClass):
    tiles = [
        {'data': np.uint8([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': 0, 'data_type': 'UBYTE'},
        {'data': np.uint8([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': 0, 'data_type': 'UBYTE'},
        {'data': np.uint8([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': 0, 'data_type': 'UBYTE'}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.UByteArrayTileWrapper

    java_rdd = tw.testOut(sc)
    ser = ProtoBufSerializer(tile_decoder, tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        expected_encoded = [to_pb_tile(x) for x in self.collected]

        for actual, expected in zip(self.tiles, expected_encoded):
            data = actual['data']
            rows, cols = data.shape

            self.assertEqual(expected.cols, cols)
            self.assertEqual(expected.rows, rows)
            self.assertEqual(expected.cellType.nd, actual['no_data_value'])
            self.assertEqual(expected.cellType.dataType, mapped_data_types[actual['data_type']])

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())
            self.assertTrue(actual['data'].dtype == expected['data'].dtype)
            self.assertEqual(actual['data'].shape, actual['data'].shape)


class IntTileSchemaTest(BaseTestClass):
    tiles = [
        {'data': np.int32([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': -2147483648, 'data_type': 'INT'},
        {'data': np.int32([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': -2147483648, 'data_type': 'INT'},
        {'data': np.int32([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': -2147483648, 'data_type': 'INT'}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.IntArrayTileWrapper

    java_rdd = tw.testOut(sc)
    ser = ProtoBufSerializer(tile_decoder, tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        expected_encoded = [to_pb_tile(x) for x in self.collected]

        for actual, expected in zip(self.tiles, expected_encoded):
            data = actual['data']
            rows, cols = data.shape

            self.assertEqual(expected.cols, cols)
            self.assertEqual(expected.rows, rows)
            self.assertEqual(expected.cellType.nd, actual['no_data_value'])
            self.assertEqual(expected.cellType.dataType, mapped_data_types[actual['data_type']])

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())
            self.assertTrue(actual['data'].dtype == expected['data'].dtype)
            self.assertEqual(actual['data'].shape, actual['data'].shape)


class DoubleTileSchemaTest(BaseTestClass):
    tiles = [
        {'data': np.double([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': True, 'data_type': 'DOUBLE'},
        {'data': np.double([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': True, 'data_type': 'DOUBLE'},
        {'data': np.double([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': True, 'data_type': 'DOUBLE'}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.DoubleArrayTileWrapper

    java_rdd = tw.testOut(sc)
    ser = ProtoBufSerializer(tile_decoder, tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        expected_encoded = [to_pb_tile(x) for x in self.collected]

        for actual, expected in zip(self.tiles, expected_encoded):
            data = actual['data']
            rows, cols = data.shape

            self.assertEqual(expected.cols, cols)
            self.assertEqual(expected.rows, rows)
            self.assertTrue(math.isnan(expected.cellType.nd))
            self.assertEqual(expected.cellType.dataType, mapped_data_types[actual['data_type']])

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())
            self.assertTrue(actual['data'].dtype == expected['data'].dtype)
            self.assertEqual(actual['data'].shape, actual['data'].shape)


class FloatTileSchemaTest(BaseTestClass):
    tiles = [
        {'data': np.float32([0, 0, 1, 1]).reshape(2, 2), 'no_data_value': True, 'data_type': 'FLOAT'},
        {'data': np.float32([1, 2, 3, 4]).reshape(2, 2), 'no_data_value': True, 'data_type': 'FLOAT'},
        {'data': np.float32([5, 6, 7, 8]).reshape(2, 2), 'no_data_value': True, 'data_type': 'FLOAT'}
    ]

    sc = BaseTestClass.pysc._jsc.sc()
    tw = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.FloatArrayTileWrapper

    java_rdd = tw.testOut(sc)
    ser = ProtoBufSerializer(tile_decoder, tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_tiles(self):
        expected_encoded = [to_pb_tile(x) for x in self.collected]

        for actual, expected in zip(self.tiles, expected_encoded):
            data = actual['data']
            rows, cols = data.shape

            self.assertEqual(expected.cols, cols)
            self.assertEqual(expected.rows, rows)
            self.assertTrue(math.isnan(expected.cellType.nd))
            self.assertEqual(expected.cellType.dataType, mapped_data_types[actual['data_type']])

    def test_decoded_tiles(self):
        for actual, expected in zip(self.collected, self.tiles):
            self.assertTrue((actual['data'] == expected['data']).all())
            self.assertTrue(actual['data'].dtype == expected['data'].dtype)
            self.assertEqual(actual['data'].shape, actual['data'].shape)


if __name__ == "__main__":
    unittest.main()
