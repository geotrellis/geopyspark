import unittest
import numpy as np

from geopyspark.geotrellis.constants import SPATIAL
from geopyspark.geotrellis.rdd import TiledRasterRDD
from geopyspark.tests.base_test_class import BaseTestClass


class LocalOpertaionsTest(BaseTestClass):
    extent = {'xmin': 0.0, 'ymin': 0.0, 'xmax': 33.0, 'ymax': 33.0}
    layout = {'layoutCols': 1, 'layoutRows': 1, 'tileCols': 4, 'tileRows': 4}
    metadata = {'cellType': 'float32ud-1.0',
                'extent': extent,
                'crs': '+proj=longlat +datum=WGS84 +no_defs ',
                'bounds': {
                    'minKey': {'col': 0, 'row': 0},
                    'maxKey': {'col': 0, 'row': 0}},
                'layoutDefinition': {
                    'extent': extent,
                    'tileLayout': {'tileCols': 4, 'tileRows': 4, 'layoutCols': 1, 'layoutRows': 1}}}

    spatial_key = {'col': 0, 'row': 0}

    def test_add_int(self):
        arr = np.zeros((1, 4, 4))

        tile = {'data': arr, 'no_data_value': -500}
        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.spatial_key, tile)])
        tiled = TiledRasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd, self.metadata)

        result = tiled + 1
        actual = result.to_numpy_rdd().first()[1]['data']

        self.assertTrue((actual == 1).all())

    def test_subtract_double(self):
        arr = np.array([[[1.0, 1.0, 1.0, 1.0],
                         [2.0, 2.0, 2.0, 2.0],
                         [3.0, 3.0, 3.0, 3.0],
                         [4.0, 4.0, 4.0, 4.0]]], dtype=float)

        tile = {'data': arr, 'no_data_value': -500}
        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.spatial_key, tile)])
        tiled = TiledRasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd, self.metadata)

        result = 5.0 - tiled
        actual = result.to_numpy_rdd().first()[1]['data']

        expected = np.array([[[4.0, 4.0, 4.0, 4.0],
                              [3.0, 3.0, 3.0, 3.0],
                              [2.0, 2.0, 2.0, 2.0],
                              [1.0, 1.0, 1.0, 1.0]]], dtype=float)

        self.assertTrue((actual == expected).all())

    def test_multiply_double(self):
        arr = np.array([[[1.0, 1.0, 1.0, 1.0],
                         [2.0, 2.0, 2.0, 2.0],
                         [3.0, 3.0, 3.0, 3.0],
                         [4.0, 4.0, 4.0, 4.0]]], dtype=float)

        tile = {'data': arr, 'no_data_value': float('nan')}
        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.spatial_key, tile)])
        tiled = TiledRasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd, self.metadata)

        result = 5.0 * tiled
        actual = result.to_numpy_rdd().first()[1]['data']

        expected = np.array([[[5.0, 5.0, 5.0, 5.0],
                              [10.0, 10.0, 10.0, 10.0],
                              [15.0, 15.0, 15.0, 15.0],
                              [20.0, 20.0, 20.0, 20.0]]], dtype=float)

        self.assertTrue((actual == expected).all())

    def test_divide_tiled_rdd(self):
        arr = np.array([[[5.0, 5.0, 5.0, 5.0],
                         [5.0, 5.0, 5.0, 5.0],
                         [5.0, 5.0, 5.0, 5.0],
                         [5.0, 5.0, 5.0, 5.0]]], dtype=float)

        divider = np.array([[[1.0, 1.0, 1.0, 1.0],
                             [1.0, 1.0, 1.0, 1.0],
                             [1.0, 1.0, 1.0, 1.0],
                             [1.0, 1.0, 1.0, 1.0]]], dtype=float)

        tile = {'data': arr, 'no_data_value': float('nan')}
        tile2 = {'data': divider, 'no_data_value': float('nan')}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.spatial_key, tile)])
        rdd2 = BaseTestClass.geopysc.pysc.parallelize([(self.spatial_key, tile2)])

        tiled = TiledRasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd, self.metadata)
        tiled2 = TiledRasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd2, self.metadata)

        result = tiled / tiled2
        actual = result.to_numpy_rdd().first()[1]['data']

        self.assertTrue((actual == 5.0).all())

    def test_combined_operations(self):
        arr = np.array([[[10, 10, 10, 10],
                         [20, 20, 20, 20],
                         [10, 10, 10, 10],
                         [20, 20, 20, 20]]], dtype=int)

        tile = {'data': arr, 'no_data_value': -500}

        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.spatial_key, tile)])

        tiled = TiledRasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd, self.metadata)

        result = (tiled + tiled) / 2
        actual = result.to_numpy_rdd().first()[1]['data']

        self.assertTrue((actual == arr).all())


if __name__ == "__main__":
    unittest.main()
