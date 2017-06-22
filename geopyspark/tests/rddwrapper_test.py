import os
import sys
import numpy as np
import pytest
import unittest

from geopyspark.geotrellis.rdd import RasterRDD
from geopyspark.geotrellis.constants import SPATIAL
from geopyspark.tests.base_test_class import BaseTestClass
from pyspark.storagelevel import StorageLevel

class RDDWrapperTest(BaseTestClass):
    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_persist(self):
        arr = np.array([[[1, 1, 1, 1]],
                        [[2, 2, 2, 2]],
                        [[3, 3, 3, 3]],
                        [[4, 4, 4, 4]]], dtype=int)
        tile = {'data': arr, 'no_data_value': -500, 'data_type': 'INT'}

        rdd = BaseTestClass.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.pysc, SPATIAL, rdd)

        self.assertEqual(raster_rdd.is_cached, False)

        raster_rdd.persist(StorageLevel.MEMORY_ONLY)
        self.assertEqual(raster_rdd.is_cached, True)

        raster_rdd.unpersist()
        self.assertEqual(raster_rdd.is_cached, False)

if __name__ == "__main__":
    unittest.main()
