import os
import unittest
import rasterio
import numpy as np
import pytest

from geopyspark.geotrellis import Extent, ProjectedExtent
from geopyspark.geotrellis.constants import SPATIAL, HOT
from geopyspark.geotrellis.rdd import RasterRDD
from geopyspark.geotrellis.render import PngRDD
from geopyspark.tests.base_test_class import BaseTestClass


class PngRddTest(BaseTestClass):

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_if_working(self):
        '''
        arr = np.zeros((1, 16, 16))
        epsg_code = 3857
        extent = Extent(0.0, 0.0, 10.0, 10.0)
        projected_extent = ProjectedExtent(extent, epsg_code)

        tile = {'data': arr, 'no_data_value': False, 'data_type': 'FLOAT'}

        rdd = BaseTestClass.pysc.parallelize([(projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        laid_out = raster_rdd.to_tiled_layer()

        result = PngRDD.makePyramid(laid_out, HOT)
        '''

    ## TODO: add more specific test if/when we can color map directly from TiledRasterRDD

if __name__ == "__main__":
    unittest.main()
