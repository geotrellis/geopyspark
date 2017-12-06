import unittest
import os
import pytest

import geopyspark as gps
import geopyspark.rasterio.read as grr
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.tests.python_test_utils import geotiff_test_path


class CatalogTest(BaseTestClass):
    uri = geotiff_test_path("srtm_52_11.tif")

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_pretiles(self):
        pretiles = grr.uri_to_pretiles(self.uri, lambda n: '+proj=longlat +datum=WGS84 +no_defs ')
        self.assertEqual(len(pretiles), 144)

    def test_tiles(self):
        pretiles = grr.uri_to_pretiles(self.uri, lambda n: '+proj=longlat +datum=WGS84 +no_defs ')
        tiles = [grr.pretile_to_tile(pretile) for pretile in pretiles]
        self.assertEqual(len(tiles), 144)

    # def test_layer(self):
    #     to_pretiles = lambda uri: grr.uri_to_pretiles(uri, lambda n: '+proj=longlat +datum=WGS84 +no_defs ')
    #     rdd0 = BaseTestClass.pysc.parallelize([geotiff_test_path("srtm_52_11.tif")])
    #     rdd1 = rdd0.flatMap(to_pretiles)
    #     rdd2 = rdd1.map(grr.pretile_to_tile)
    #     rdd3 = gps.RasterLayer.from_numpy_rdd(gps.LayerType.SPATIAL, rdd2)
    #     self.assertEqual(rdd1.count(), 144)

if __name__ == "__main__":
    unittest.main()
