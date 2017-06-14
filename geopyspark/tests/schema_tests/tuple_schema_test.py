import os
import unittest
import pytest
import numpy as np

from pyspark import RDD
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.geotrellis import Extent, ProjectedExtent
from geopyspark.protobufserializer import ProtoBufSerializer
from geopyspark.protobufregistry import ProtoBufRegistry
from geopyspark.tests.base_test_class import BaseTestClass

from geopyspark.protobuf import tupleMessages_pb2


class TupleSchemaTest(BaseTestClass):
    extent = {
        'epsg': 2004,
        'extent': {'xmax': 1.0, 'xmin': 0.0, 'ymax': 1.0, 'ymin': 0.0},
        'proj4': None
    }

    arr = np.int8([0, 0, 1, 1]).reshape(2, 2)
    bands = [arr, arr, arr]
    multiband_tile = np.array(bands)
    multiband_dict = {'data': multiband_tile, 'no_data_value': -128, 'data_type': 'BYTE'}

    sc = BaseTestClass.geopysc.pysc._jsc.sc()
    ew = BaseTestClass.geopysc.pysc._jvm.geopyspark.geotrellis.tests.schemas.TupleWrapper

    java_rdd = ew.testOut(sc)

    decoder = ProtoBufRegistry.create_partial_tuple_decoder(key_type="ProjectedExtent")
    encoder = ProtoBufRegistry.create_partial_tuple_encoder(key_type="ProjectedExtent")

    ser = ProtoBufSerializer(decoder, encoder)
    rdd = RDD(java_rdd, BaseTestClass.geopysc.pysc, AutoBatchedSerializer(ser))
    collected = rdd.collect()

    @pytest.mark.skipif('TRAVIS' in os.environ,
                         reason="Encoding using methods in Main causes issues on Travis")
    def test_encoded_tuples(self):
        proto_tuple = tupleMessages_pb2.ProtoTuple()

        self.extent['extent'] = Extent(**self.extent['extent'])
        proto_extent = ProjectedExtent(**self.extent).to_protobuf_projected_extent
        proto_multiband = ProtoBufRegistry._multibandtile_encoder(self.multiband_dict)

        proto_tuple.projectedExtent.CopyFrom(proto_extent)
        proto_tuple.tiles.CopyFrom(proto_multiband)

        bs = proto_tuple.SerializeToString()
        expected_encoded = [self.ser.dumps(x) for x in self.collected]

        for expected in expected_encoded:
            self.assertEqual(bs, expected)

    def test_decoded_tuples(self):
        expected_tuples = [
            (self.extent, self.multiband_dict),
            (self.extent, self.multiband_dict),
            (self.extent, self.multiband_dict)
        ]

        for actual, expected in zip(self.collected, expected_tuples):
            (actual_extent, actual_tile) = actual
            (expected_extent, expected_tile) = expected

            self.assertTrue((actual_tile['data'] == expected_tile['data']).all())
            self.assertDictEqual(actual_extent._asdict(), expected_extent)


if __name__ == "__main__":
    unittest.main()
