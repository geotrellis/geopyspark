import os
import unittest
import numpy as np

import pytest

from shapely.geometry import Point
from geopyspark.geotrellis import SpatialKey
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.geotrellis.rdd import TiledRasterRDD
from geopyspark.geotrellis.constants import SPATIAL


class CostDistanceTest(BaseTestClass):
    data = np.array([[
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 0.0]]])

    layer = [(SpatialKey(0, 0), {'no_data_value': -1.0, 'data': data, 'data_type': 'FLOAT'}),
             (SpatialKey(1, 0), {'no_data_value': -1.0, 'data': data, 'data_type': 'FLOAT'}),
             (SpatialKey(0, 1), {'no_data_value': -1.0, 'data': data, 'data_type': 'FLOAT'}),
             (SpatialKey(1, 1), {'no_data_value': -1.0, 'data': data, 'data_type': 'FLOAT'})]
    rdd = BaseTestClass.pysc.parallelize(layer)

    extent = {'xmin': 0.0, 'ymin': 0.0, 'xmax': 33.0, 'ymax': 33.0}
    layout = {'layoutCols': 2, 'layoutRows': 2, 'tileCols': 5, 'tileRows': 5}
    metadata = {'cellType': 'float32ud-1.0',
                'extent': extent,
                'crs': '+proj=longlat +datum=WGS84 +no_defs ',
                'bounds': {
                    'minKey': {'col': 0, 'row': 0},
                    'maxKey': {'col': 1, 'row': 1}},
                'layoutDefinition': {
                    'extent': extent,
                    'tileLayout': {'tileCols': 5, 'tileRows': 5, 'layoutCols': 2, 'layoutRows': 2}}}

    raster_rdd = TiledRasterRDD.from_numpy_rdd(BaseTestClass.pysc, SPATIAL, rdd, metadata)

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_costdistance_finite(self):
        def zero_one(kv):
            k = kv[0]
            return (k.col == 0 and k.row == 1)

        result = self.raster_rdd.cost_distance(geometries=[Point(13, 13)], max_distance=144000.0)

        tile = result.to_numpy_rdd().filter(zero_one).first()[1]
        point_distance = tile['data'][0][1][3]
        self.assertEqual(point_distance, 0.0)

    def test_costdistance_finite_int(self):
        def zero_one(kv):
            k = kv[0]
            return (k.col == 0 and k.row == 1)

        result = self.raster_rdd.cost_distance(geometries=[Point(13, 13)], max_distance=144000)

        tile = result.to_numpy_rdd().filter(zero_one).first()[1]
        point_distance = tile['data'][0][1][3]
        self.assertEqual(point_distance, 0.0)

    def test_costdistance_infinite(self):
        def zero_one(kv):
            k = kv[0]
            return (k.col == 0 and k.row == 1)

        result = self.raster_rdd.cost_distance(geometries=[Point(13, 13)], max_distance=float('inf'))

        tile = result.to_numpy_rdd().filter(zero_one).first()[1]
        point_distance = tile['data'][0][0][0]
        self.assertTrue(point_distance > 1250000)

if __name__ == "__main__":
    unittest.main()
