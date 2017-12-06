import unittest
import os
import pytest

# from shapely.geometry import box

# from geopyspark.geotrellis import Extent, SpatialKey, GlobalLayout, LocalLayout
# from geopyspark.geotrellis.catalog import read_value, query, read_layer_metadata, AttributeStore
# from geopyspark.geotrellis.constants import LayerType
# from geopyspark.geotrellis.geotiff import get
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


if __name__ == "__main__":
    unittest.main()
