import os
import unittest
import numpy as np

from geopyspark.geotrellis.rdd import TiledRasterRDD
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.geotrellis.constants import SPATIAL, SUM, MIN, SQUARE, ANNULUS


class FocalTest(BaseTestClass):
    data = np.array([[
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 0.0]]])

    layer = [({'row': 0, 'col': 0}, {'no_data_value': -1.0, 'data': data}),
             ({'row': 1, 'col': 0}, {'no_data_value': -1.0, 'data': data}),
             ({'row': 0, 'col': 1}, {'no_data_value': -1.0, 'data': data}),
             ({'row': 1, 'col': 1}, {'no_data_value': -1.0, 'data': data})]
    rdd = BaseTestClass.geopysc.pysc.parallelize(layer)

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

    raster_rdd = TiledRasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd, metadata)

    def test_focal_sum(self):
        result = self.raster_rdd.focal(
            operation=SUM,
            neighborhood=SQUARE,
            param_1=1.0)

        self.assertTrue(result.to_numpy_rdd().first()[1]['data'][0][1][0] >= 6)

    def test_focal_min(self):
        result = self.raster_rdd.focal(operation=MIN, neighborhood=ANNULUS, param_1=2.0, param_2=1.0)

        self.assertEqual(result.to_numpy_rdd().first()[1]['data'][0][0][0], -1)


if __name__ == "__main__":
    unittest.main()
    BaseTestClass.geopysc.pysc.stop()
