from geopyspark.tests.python_test_utils import add_spark_path
add_spark_path()

from pyspark import SparkContext, RDD
from geopyspark.geotrellis.extent import Extent
from geopyspark.geotrellis.tile import TileArray
from geopyspark.avroregistry import AvroRegistry

import unittest
import numpy as np


class MyCustomClass(object):
    def __init__(self, extents, tile):
        self.extents = extents
        self.tile = tile

    @staticmethod
    def decoding_method(i):
        extents = AvroRegistry.tuple_decoder(i['extents'],
                AvroRegistry.extent_decoder,
                AvroRegistry.extent_decoder)

        tile = AvroRegistry.tile_decoder(i['tile'])

        return MyCustomClass(extents, tile)

    @staticmethod
    def encoding_method(obj):
        extents = AvroRegistry.tuple_encoder(obj.extents,
                AvroRegistry.extent_encoder,
                AvroRegistry.extent_encoder)

        tile = AvroRegistry.tile_encoder(obj.tile)

        datum = {
                'extents': extents,
                'tile': tile
                }

        return datum

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return NotImplemented

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return NotImplemented

    def __repr__(self):
        return "MyCustomClass(Extents: {}, Tile: {}".format(self.extents, self.tile)


class TestCustomClass(unittest.TestCase):
    e1 = Extent(0, 1, 2, 3)
    e2 = Extent(4, 5, 6, 7)
    tile = TileArray(np.array([0, 1, 2, 3, 4, 5]).reshape(2, 3), no_data_value=-5)

    custom_cls = MyCustomClass((e1, e2), tile)
    custom_cls_schema = custom_cls.encoding_method(custom_cls)

    ar = AvroRegistry()

    def test_encoding(self):
        self.ar.add_encoder(self.custom_cls, self.custom_cls.encoding_method)

        encoder = self.ar.get_encoder(self.custom_cls)
        actual_encoded = encoder(self.custom_cls)
        expected_encoded = self.custom_cls.encoding_method(self.custom_cls)

        self.assertEqual(actual_encoded, expected_encoded)

    def test_decoding(self):
        self.ar.add_decoder(self.custom_cls, self.custom_cls.decoding_method)

        decoder = self.ar.get_decoder('MyCustomClass', self.custom_cls_schema)
        actual_decoded = decoder(self.custom_cls_schema)
        expected_decoded = self.custom_cls.decoding_method(self.custom_cls_schema)

        self.assertEqual(actual_decoded.extents, expected_decoded.extents)
        self.assertTrue((actual_decoded.tile == expected_decoded.tile).all())


if __name__ == "__main__":
    unittest.main()
