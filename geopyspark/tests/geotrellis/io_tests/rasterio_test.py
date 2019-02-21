import unittest
import os
import pytest
import rasterio

from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.tests.python_test_utils import file_path


class CatalogTest(BaseTestClass):
    uri = file_path("srtm_52_11.tif")

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    @pytest.mark.skipif('TRAVIS_PYTHON_VERSION' in os.environ.keys(),
                        reason="Travis produces different results than local")
    def test_tiles(self):
        import geopyspark as gps
        from geopyspark.geotrellis import rasterio
        tiles = rasterio._read_windows(self.uri, xcols=256, ycols=256, bands=None, crs_to_proj4=lambda n: '+proj=longlat +datum=WGS84 +no_defs ')
        self.assertEqual(len(list(tiles)), 144)

    @pytest.mark.skipif('TRAVIS_PYTHON_VERSION' in os.environ.keys(),
                        reason="Travis produces different results than local")
    def test_layer(self):
        import geopyspark as gps
        from geopyspark.geotrellis import rasterio
        rdd0 = gps.rasterio.get(self.uri)
        rdd1 = gps.RasterLayer.from_numpy_rdd(gps.LayerType.SPATIAL, rdd0)
        self.assertEqual(rdd1.count(), 144)

if __name__ == "__main__":
    unittest.main()
