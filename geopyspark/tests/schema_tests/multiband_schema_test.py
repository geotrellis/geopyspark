import unittest
import numpy as np

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.avroserializer import AvroSerializer
from geopyspark.avroregistry import AvroRegistry
from geopyspark.tests.base_test_class import BaseTestClass


class MultibandSchemaTest(BaseTestClass):
    arr = np.array(bytearray([0, 0, 1, 1])).reshape(2, 2)
    no_data = -128
    arr_dict = {'data': arr, 'no_data_value': no_data}
    band_dicts = [arr_dict, arr_dict, arr_dict]

    bands = [arr, arr, arr]
    multiband_tile = np.array(bands)
    multiband_dict = {'data': multiband_tile, 'no_data_value': no_data}

    sc = BaseTestClass.geopysc.pysc._jsc.sc()
    mw = BaseTestClass.geopysc.pysc._jvm.geopyspark.geotrellis.tests.schemas.ArrayMultibandTileWrapper

    tup = mw.testOut(sc)
    java_rdd = tup._1()

    ser = AvroSerializer(tup._2(),
                         AvroRegistry.tile_decoder,
                         AvroRegistry.tile_encoder)

    rdd = RDD(java_rdd, BaseTestClass.geopysc.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    def test_encoded_multibands(self):
        encoded = self.rdd.map(lambda s: AvroRegistry.tile_encoder(s))

        actual_encoded = encoded.collect()[0]
        expected_encoded = AvroRegistry.tile_encoder(self.multiband_dict)

        for actual, expected in zip(actual_encoded['bands'], expected_encoded['bands']):
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
