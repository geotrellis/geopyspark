import os
import unittest
import numpy as np

from shapely.geometry import Point
from geopyspark.geotrellis.rdd import TiledRasterRDD
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.geotrellis.constants import SPATIAL


class StitchTest(BaseTestClass):
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

    def test_stitch(self):
        result = self.raster_rdd.stitch()

        self.assertTrue(result['data'].shape == (1, 10, 10))


if __name__ == "__main__":
    unittest.main()
