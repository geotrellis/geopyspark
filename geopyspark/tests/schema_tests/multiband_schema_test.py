import unittest
import numpy as np
import pytest

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.geotrellis.protobuf import tileMessages_pb2
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.geotrellis.protobufcodecs import multibandtile_decoder, multibandtile_encoder
from geopyspark.tests.base_test_class import BaseTestClass


class MultibandSchemaTest(BaseTestClass):
    arr = np.int8([0, 0, 1, 1]).reshape(2, 2)
    no_data = -128
    arr_dict = {'data': arr, 'no_data_value': no_data, 'data_type': 'BYTE'}
    band_dicts = [arr_dict, arr_dict, arr_dict]

    bands = [arr, arr, arr]
    multiband_tile = np.array(bands)
    multiband_dict = {'data': multiband_tile, 'no_data_value': no_data, 'data_type': 'BYTE'}

    sc = BaseTestClass.pysc._jsc.sc()
    mw = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.tests.schemas.ArrayMultibandTileWrapper

    java_rdd = mw.testOut(sc)
    ser = ProtoBufSerializer(multibandtile_decoder, multibandtile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_encoded_multibands(self):
        actual_encoded = [multibandtile_encoder(x) for x in self.collected]

        proto_tile = tileMessages_pb2.ProtoTile()
        cell_type = tileMessages_pb2.ProtoCellType()

        cell_type.nd = self.no_data
        cell_type.hasNoData = True
        cell_type.dataType = 1

        proto_tile.cols = 2
        proto_tile.rows = 2
        proto_tile.sint32Cells.extend(self.arr.flatten().tolist())
        proto_tile.cellType.CopyFrom(cell_type)

        proto_multiband = tileMessages_pb2.ProtoMultibandTile()
        proto_multiband.tiles.extend([proto_tile, proto_tile, proto_tile])
        bs = proto_multiband.SerializeToString()

        expected_encoded = [bs, bs, bs]

        for actual, expected in zip(actual_encoded, expected_encoded):
            self.assertEqual(actual, expected)

    def test_decoded_multibands(self):
        expected_multibands = [
            self.multiband_dict,
            self.multiband_dict,
            self.multiband_dict
        ]

        for actual, expected in zip(self.collected, expected_multibands):
            self.assertTrue((actual['data'] == expected['data']).all())


if __name__ == "__main__":
    unittest.main()
