import os
import unittest
import numpy as np

import pytest

from geopyspark.geotrellis import SpatialKey
from geopyspark.geotrellis.constants import ZOOM
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.geotrellis.rdd import TiledRasterRDD
from geopyspark.geotrellis.constants import SPATIAL


class LookupTest(BaseTestClass):
    data = np.array([[
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 1.0],
        [1.0, 1.0, 1.0, 1.0, 0.0]]])

    layer = [(SpatialKey(0, 0), {'no_data_value': -1.0, 'data': data + 0, 'data_type': 'FLOAT'}),
             (SpatialKey(1, 0), {'no_data_value': -1.0, 'data': data + 1, 'data_type': 'FLOAT'}),
             (SpatialKey(0, 1), {'no_data_value': -1.0, 'data': data + 2, 'data_type': 'FLOAT'}),
             (SpatialKey(1, 1), {'no_data_value': -1.0, 'data': data + 3, 'data_type': 'FLOAT'})]
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

    def test_lookup_1(self):
        result = self.raster_rdd.lookup(0, 0)[0]
        n = np.sum(result['data'])
        self.assertEqual(n, 24 + 0*25)

    def test_lookup_2(self):
        result = self.raster_rdd.lookup(0, 1)[0]
        n = np.sum(result['data'])
        self.assertEqual(n, 24 + 2*25)

    def test_lookup_3(self):
        result = self.raster_rdd.lookup(1, 0)[0]
        n = np.sum(result['data'])
        self.assertEqual(n, 24 + 1*25)

    def test_lookup_4(self):
        result = self.raster_rdd.lookup(1, 1)[0]
        n = np.sum(result['data'])
        self.assertEqual(n, 24 + 3*25)

    def test_lookup_5(self):
        with pytest.raises(IndexError):
            result = self.raster_rdd.lookup(13, 33)


if __name__ == "__main__":
    unittest.main()
