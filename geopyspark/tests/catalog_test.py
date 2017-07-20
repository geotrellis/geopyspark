import unittest
import os
import pytest

from shapely.geometry import box

from geopyspark.geotrellis import Extent, SpatialKey, GlobalLayout
from geopyspark.geotrellis.catalog import read, read_value, query, read_layer_metadata, get_layer_ids
from geopyspark.geotrellis.constants import LayerType, LayoutScheme
from geopyspark.geotrellis.geotiff import get
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.tests.python_test_utils import geotiff_test_path


class CatalogTest(BaseTestClass):
    rdd = get(BaseTestClass.pysc, LayerType.SPATIAL, geotiff_test_path("srtm_52_11.tif"))

    metadata = rdd.collect_metadata()
    laid_out = rdd.tile_to_layout(metadata)
    gl = GlobalLayout(256, 11, 0.1)
    reprojected = laid_out.reproject(target_crs="EPSG:3857", layout=gl)
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
            actual_layer = read(BaseTestClass.pysc, LayerType.SPATIAL, self.uri, self.layer_name, x)
            expected_layer = self.result.levels[x]

            self.assertDictEqual(actual_layer.layer_metadata.to_dict(),
                                 expected_layer.layer_metadata.to_dict())

    def test_read_value1(self):
        tiled = read_value(BaseTestClass.pysc,
                           LayerType.SPATIAL,
                           self.uri,
                           self.layer_name,
                           11,
                           1450,
                           966)

        self.assertEqual(tiled.cells.shape, (1, 256, 256))

    def test_read_value2(self):
        tiled = read_value(BaseTestClass.pysc,
                           LayerType.SPATIAL,
                           self.uri,
                           self.layer_name,
                           11,
                           1450,
                           966,
                           options={'a': 0})

        self.assertEqual(tiled.cells.shape, (1, 256, 256))

    def test_read_value3(self):
        tiled = read_value(BaseTestClass.pysc,
                           LayerType.SPATIAL,
                           self.uri,
                           self.layer_name,
                           11,
                           1450,
                           966,
                           kwargs={'a': 0})

        self.assertEqual(tiled.cells.shape, (1, 256, 256))

    def test_bad_read_value(self):
        tiled = read_value(BaseTestClass.pysc,
                           LayerType.SPATIAL,
                           self.uri,
                           self.layer_name,
                           11,
                           1450,
                           2000)

        self.assertEqual(tiled, None)

    def test_query1(self):
        intersection = box(8348915.46680623, 543988.943201519, 8348915.4669, 543988.943201520)
        queried = query(BaseTestClass.pysc, LayerType.SPATIAL, self.uri, self.layer_name,
                        11, intersection,
                        options={'a': 0})

        self.assertEqual(queried.to_numpy_rdd().first()[0], SpatialKey(1450, 996))

    def test_query2(self):
        intersection = Extent(8348915.46680623, 543988.943201519, 8348915.4669, 543988.943201520)
        queried = query(BaseTestClass.pysc, LayerType.SPATIAL, self.uri, self.layer_name,
                        11, intersection,
                        query_proj=3857, kwargs={'a': 0})

        self.assertEqual(queried.to_numpy_rdd().first()[0], SpatialKey(1450, 996))

    def test_query3(self):
        intersection = box(8348915.46680623, 543988.943201519, 8348915.4669, 543988.943201520).wkb
        queried = query(BaseTestClass.pysc, LayerType.SPATIAL, self.uri, self.layer_name,
                        11, intersection)

        self.assertEqual(queried.to_numpy_rdd().first()[0], SpatialKey(1450, 996))

    def test_query4(self):
        intersection = 42
        with pytest.raises(TypeError):
            queried = query(BaseTestClass.pysc, LayerType.SPATIAL, self.uri, self.layer_name,
                            11, query_geom=intersection, numPartitions=2)
            result = queried.to_numpy_rdd().first()[0]

    def test_query_partitions(self):
        intersection = box(8348915.46680623, 543988.943201519, 8348915.4669, 543988.943201520)
        queried = query(BaseTestClass.pysc, LayerType.SPATIAL, self.uri, self.layer_name,
                        11, intersection, numPartitions=2)

        self.assertEqual(queried.to_numpy_rdd().first()[0], SpatialKey(1450, 996))

    def test_query_crs(self):
        intersection = box(8348915.46680623, 543988.943201519, 8348915.4669, 543988.943201520)
        queried = query(BaseTestClass.pysc, LayerType.SPATIAL, self.uri, self.layer_name, 11, intersection,
                        proj_query=3857)

        self.assertEqual(queried.to_numpy_rdd().first()[0], SpatialKey(1450, 996))

    def test_read_metadata_exception(self):
        uri = "abcxyz://123"
        options = {'a': 0, 'b': 1}
        with pytest.raises(ValueError):
            layer = read_layer_metadata(BaseTestClass.pysc, LayerType.SPATIAL, uri,
                                        self.layer_name, 5, options=options)

    def test_read_metadata1(self):
        layer = read(BaseTestClass.pysc, LayerType.SPATIAL, self.uri, self.layer_name, 5)
        actual_metadata = layer.layer_metadata

        expected_metadata = read_layer_metadata(BaseTestClass.pysc, LayerType.SPATIAL, self.uri,
                                                self.layer_name, 5, kwargs={'a': 0})
    def test_read_metadata2(self):
        layer = read(BaseTestClass.pysc, LayerType.SPATIAL, self.uri, self.layer_name, 5)
        actual_metadata = layer.layer_metadata

        expected_metadata = read_layer_metadata(BaseTestClass.pysc, LayerType.SPATIAL, self.uri,
                                                self.layer_name, 5)

        self.assertEqual(actual_metadata.to_dict(), expected_metadata.to_dict())

    def test_layer_ids1(self):
        ids = get_layer_ids(BaseTestClass.pysc, self.uri)

        self.assertTrue(len(ids) == 11)

    def test_layer_ids2(self):
        ids = get_layer_ids(BaseTestClass.pysc, self.uri, options={'a': 0})

        self.assertTrue(len(ids) == 11)

    def test_layer_ids3(self):
        ids = get_layer_ids(BaseTestClass.pysc, self.uri, kwargs={'a': 0})

        self.assertTrue(len(ids) == 11)


if __name__ == "__main__":
    unittest.main()
