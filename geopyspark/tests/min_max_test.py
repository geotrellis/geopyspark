import os
import sys
import numpy as np
import pytest
import unittest

from geopyspark.geotrellis import Extent, ProjectedExtent
from geopyspark.geotrellis.rdd import RasterRDD
from geopyspark.geotrellis.constants import SPATIAL
from geopyspark.tests.base_test_class import BaseTestClass


class MinMaxTest(BaseTestClass):
    epsg_code = 3857
    extent = Extent(0.0, 0.0, 10.0, 10.0)
    projected_extent = ProjectedExtent(extent, epsg_code)

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_all_zeros(self):
        arr = np.zeros((1, 16, 16)).astype('int')
        tile = {'data': arr, 'no_data_value': -500, 'data_type': 'INT'}

        rdd = BaseTestClass.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.pysc, SPATIAL, rdd)
        min_max = raster_rdd.get_min_max()

        self.assertEqual((0.0, 0.0), min_max)

    def test_multibands(self):
        arr = np.array([[[1, 1, 1, 1]],
                        [[2, 2, 2, 2]],
                        [[3, 3, 3, 3]],
                        [[4, 4, 4, 4]]], dtype=int)
        tile = {'data': arr, 'no_data_value': -500, 'data_type': 'INT'}

        rdd = BaseTestClass.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.pysc, SPATIAL, rdd)
        min_max = raster_rdd.get_min_max()

        self.assertEqual((1.0, 4.0), min_max)

    def test_floating(self):
        arr = np.array([[[0.0, 0.0, 0.0, 0.0],
                         [1.0, 1.0, 1.0, 1.0],
                         [1.5, 1.5, 1.5, 1.5],
                         [2.0, 2.0, 2.0, 2.0]]], dtype=float)

        tile = {'data': arr, 'no_data_value': float('nan'), 'data_type': 'FLOAT'}
        rdd = BaseTestClass.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.pysc, SPATIAL, rdd)
        min_max = raster_rdd.get_min_max()

        self.assertEqual((0.0, 2.0), min_max)

if __name__ == "__main__":
    unittest.main()
