import unittest
import os
import pytest

from shapely.geometry import box

from geopyspark.geotrellis import SpatialKey
from geopyspark.geotrellis.catalog import read, read_value, query, read_layer_metadata, get_layer_ids
from geopyspark.geotrellis.constants import SPATIAL, ZOOM
from geopyspark.geotrellis.geotiff_rdd import get
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.tests.python_test_utils import geotiff_test_path


class CatalogTest(BaseTestClass):
    rdd = get(BaseTestClass.pysc, SPATIAL, geotiff_test_path("srtm_52_11.tif"))

    metadata = rdd.collect_metadata()
    laid_out = rdd.tile_to_layout(metadata)
    reprojected = laid_out.reproject(target_crs="EPSG:3857", scheme=ZOOM)
    result = reprojected.pyramid(start_zoom=11, end_zoom=1)

    dir_path = geotiff_test_path("catalog/")
    uri = "file://{}".format(dir_path)
    layer_name = "catalog-test"

    @pytest.fixture(scope='class', autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_read(self):
        for x in range(11, 0, -1):
            actual_layer = read(BaseTestClass.pysc, SPATIAL, self.uri, self.layer_name, x)
            expected_layer = self.result.levels[x]

            self.assertDictEqual(actual_layer.layer_metadata.to_dict(),
                                 expected_layer.layer_metadata.to_dict())

    def test_read_value(self):
        tiled = read_value(BaseTestClass.pysc,
                           SPATIAL,
                           self.uri,
                           self.layer_name,
                           11,
                           1450,
                           966)

        self.assertEqual(tiled['data'].shape, (1, 256, 256))

    def test_bad_read_value(self):
        tiled = read_value(BaseTestClass.pysc,
                           SPATIAL,
                           self.uri,
                           self.layer_name,
                           11,
                           1450,
                           2000)

        self.assertEqual(tiled, None)

    def test_query(self):
        intersection = box(8348915.46680623, 543988.943201519, 8348915.4669, 543988.943201520)
        queried = query(BaseTestClass.pysc, SPATIAL, self.uri, self.layer_name, 11, intersection)

        self.assertEqual(queried.to_numpy_rdd().first()[0], SpatialKey(1450, 996))

    def test_query_partitions(self):
        intersection = box(8348915.46680623, 543988.943201519, 8348915.4669, 543988.943201520)
        queried = query(BaseTestClass.pysc, SPATIAL, self.uri, self.layer_name, 11, intersection,
                        numPartitions=2)
        self.assertEqual(queried.to_numpy_rdd().first()[0], SpatialKey(1450, 996))

    def test_query_crs(self):
        intersection = box(8348915.46680623, 543988.943201519, 8348915.4669, 543988.943201520)
        queried = query(BaseTestClass.pysc, SPATIAL, self.uri, self.layer_name, 11, intersection,
                        proj_query=3857)

        self.assertEqual(queried.to_numpy_rdd().first()[0], SpatialKey(1450, 996))

    def test_read_metadata(self):
        layer = read(BaseTestClass.pysc, SPATIAL, self.uri, self.layer_name, 5)
        actual_metadata = layer.layer_metadata

        expected_metadata = read_layer_metadata(BaseTestClass.pysc, SPATIAL, self.uri,
                                                self.layer_name, 5)

        self.assertEqual(actual_metadata.to_dict(), expected_metadata.to_dict())

    def test_layer_ids(self):
        ids = get_layer_ids(BaseTestClass.pysc, self.uri)

        self.assertTrue(len(ids) == 11)


if __name__ == "__main__":
    unittest.main()
