import os
import unittest
import numpy as np

from shapely.geometry import Polygon
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.geotrellis.rdd import TiledRasterRDD
from geopyspark.geotrellis.constants import SPATIAL


class RasterizeTest(BaseTestClass):
    extent = {'xmin': 0.0, 'ymin': 0.0, 'xmax': 11.0, 'ymax': 11.0}

    def test_whole_area(self):
        polygon = Polygon([(0, 11), (11, 11), (11, 0), (0, 0)])

        raster_rdd = TiledRasterRDD.rasterize(BaseTestClass.geopysc,
                                              SPATIAL,
                                              polygon,
                                              self.extent,
                                              "EPSG:3857",
                                              11,
                                              11,
                                              1)

        data = raster_rdd.to_numpy_rdd().first()[1]['data']

        self.assertEqual(data.shape, (1, 11, 11))
        self.assertTrue((data == 1).all())


if __name__ == "__main__":
    unittest.main()
