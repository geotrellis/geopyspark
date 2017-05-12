import os
import sys
import math
import numpy as np
import unittest

from geopyspark.geotrellis.rdd import RasterRDD
from geopyspark.geotrellis.constants import SPATIAL, NODATAINT, LESSTHAN, GREATERTHAN
from geopyspark.tests.base_test_class import BaseTestClass


class ReclassifyTest(BaseTestClass):
    epsg_code = 3857
    extent = {'xmin': 0.0, 'ymin': 0.0, 'xmax': 10.0, 'ymax': 10.0}

    projected_extent = {'extent': extent, 'epsg': epsg_code}

    def test_all_zeros(self):
        arr = np.zeros((1, 16, 16))
        tile = {'data': arr, 'no_data_value': -500}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        value_map = {0: 1}

        result = raster_rdd.reclassify(value_map, int).to_numpy_rdd().first()[1]['data']

        self.assertTrue((result == 1).all())

    def test_various_values(self):
        arr = np.array([[[1, 1, 1, 1],
                         [2, 2, 2, 2],
                         [3, 3, 3, 3],
                         [4, 4, 4, 4]]], dtype=int)
        tile = {'data': arr, 'no_data_value': -500}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        value_map = {1: 10, 3: 17}

        result = raster_rdd.reclassify(value_map, int).to_numpy_rdd().first()[1]['data']

        expected = np.array([[[10, 10, 10, 10],
                              [17, 17, 17, 17],
                              [17, 17, 17, 17],
                              [-500, -500, -500, -500]]], dtype=int)

        self.assertTrue((result == expected).all())

    def test_ranges(self):
        arr = np.array([[[1, 1, 1, 1],
                         [2, 2, 2, 2],
                         [3, 3, 3, 3],
                         [4, 4, 4, 4]]], dtype=int)
        tile = {'data': arr, 'no_data_value': -500}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        value_map = {2: 20}

        result = raster_rdd.reclassify(value_map, int, GREATERTHAN).to_numpy_rdd().first()[1]['data']

        expected = np.array([[[-500, -500, -500, -500],
                              [-500, -500, -500, -500],
                              [20, 20, 20, 20],
                              [20, 20, 20, 20]]], dtype=int)

        self.assertTrue((result == expected).all())

    def test_multibands(self):
        arr = np.array([[[1, 1, 1, 1]],
                        [[2, 2, 2, 2]],
                        [[3, 3, 3, 3]],
                        [[4, 4, 4, 4]]], dtype=int)
        tile = {'data': arr, 'no_data_value': -500}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        value_map = {3: 10, 4: 20}

        result = raster_rdd.reclassify(value_map, int).to_numpy_rdd().first()[1]['data']

        expected = np.array([[[10, 10, 10, 10]],
                             [[10, 10, 10, 10]],
                             [[10, 10, 10, 10]],
                             [[20, 20, 20, 20]]], dtype=int)

        self.assertTrue((result == expected).all())

    def test_floating_voint_ranges(self):
        arr = np.array([[[0.0, 0.0, 0.0, 0.0],
                         [1.0, 1.0, 1.0, 1.0],
                         [1.5, 1.5, 1.5, 1.5],
                         [2.0, 2.0, 2.0, 2.0]]], dtype=float)

        tile = {'data': arr, 'no_data_value': float('nan')}
        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        value_map = {2.0: 5.0}

        result = raster_rdd.reclassify(value_map, float, LESSTHAN).to_numpy_rdd().first()[1]['data']

        expected = np.array([[[5.0, 5.0, 5.0, 5.0],
                              [5.0, 5.0, 5.0, 5.0],
                              [5.0, 5.0, 5.0, 5.0]]], dtype=float)

        self.assertTrue((result[0, 2, ] == expected).all())
        for x in result[0, 3, ]:
            self.assertTrue(math.isnan(x))

    def test_no_data_ints(self):
        arr = np.zeros((1, 16, 16))
        tile = {'data': arr, 'no_data_value': NODATAINT}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        value_map = {0: NODATAINT}

        result = raster_rdd.reclassify(value_map, int).to_numpy_rdd().first()[1]['data']

        self.assertTrue((result == NODATAINT).all())

    def test_no_data_floats(self):
        arr = np.array([[[0.0, 0.0, 0.0, 0.0],
                         [0.0, 0.0, 0.0, 0.0],
                         [0.0, 0.0, 0.0, 0.0],
                         [0.0, 0.0, 0.0, 0.0]]], dtype=float)
        tile = {'data': arr, 'no_data_value': float('nan')}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        value_map = {0.0: float('nan')}

        result = raster_rdd.reclassify(value_map, float).to_numpy_rdd().first()[1]['data']

        for x in list(result.flatten()):
            self.assertTrue(math.isnan(x))

    def test_ignore_no_data_ints(self):
        arr = np.ones((1, 16, 16), int)
        np.fill_diagonal(arr[0], NODATAINT)
        tile = {'data': arr, 'no_data_value': NODATAINT}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        value_map = {1: 0}

        result = raster_rdd.reclassify(value_map, int, replace_nodata_with=1).to_numpy_rdd().first()[1]['data']

        self.assertTrue((result == np.identity(16, int)).all())

    def test_ignore_no_data_floats(self):
        arr = np.ones((1, 4, 4))
        np.fill_diagonal(arr[0], float('nan'))
        tile = {'data': arr, 'no_data_value': float('nan')}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        value_map = {1.0: 0.0}

        result = raster_rdd.reclassify(value_map, float, replace_nodata_with=1.0).to_numpy_rdd().first()[1]['data']

        self.assertTrue((result == np.identity(4)).all())

if __name__ == "__main__":
    unittest.main()
