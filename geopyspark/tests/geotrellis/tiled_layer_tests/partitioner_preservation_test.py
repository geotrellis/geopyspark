import unittest
import os
import pytest

from shapely.geometry import box

from geopyspark.geotrellis import Extent, SpatialKey, GlobalLayout, LocalLayout, Partitioner
from geopyspark.geotrellis.constants import LayerType, Operation#, Partitioner
from geopyspark.geotrellis.neighborhood import Square
from geopyspark.geotrellis.geotiff import get
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.tests.python_test_utils import file_path


class PartitionerPreservationTest(BaseTestClass):
    rdd = get(LayerType.SPATIAL, file_path("srtm_52_11.tif"), max_tile_size=6001)
    tiled_layer = rdd.tile_to_layout()

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_preservation(self):
        max_layer = self.tiled_layer.focal(Operation.MAX,
                                           Square(2),
                                           partitioner=Partitioner.create_spatial_partitioner(2))

        print(max_layer.partitioner())#, max_layer.getNumPartitions())
        #self.assertEqual(max_layer.partitioner(), Partitioner.SPATIAL_PARTITIONER)

        #reprojected_layer = max_layer.tile_to_layout(LocalLayout(), 3857)

        #self.assertEqual(reprojected_layer.partitioner(), Partitioner.SPATIAL_PARTITIONER)


if __name__ == "__main__":
    unittest.main()
