import os
import unittest
import pytest

from geopyspark.geotrellis import LayoutDefinition, LocalLayout, GlobalLayout
from geopyspark.geotrellis.constants import LayoutScheme
from geopyspark.tests.base_test_class import BaseTestClass


class ReprojectTest(BaseTestClass):
    metadata = BaseTestClass.rdd.collect_metadata(extent=BaseTestClass.extent,
                                                  layout=BaseTestClass.layout)

    crs = metadata.crs
    expected_crs = "+proj=longlat +ellps=WGS72 +towgs84=0,0,1.9,0,0,0.814,-0.38 +no_defs "

    laid_out_rdd = BaseTestClass.rdd.tile_to_layout(metadata)

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_invalid(self):
        with pytest.raises(TypeError):
            self.laid_out_rdd.reproject(4326, layout=self.extent)

    def test_repartition(self):
        result = self.laid_out_rdd.repartition(2)
        self.assertEqual(result.getNumPartitions(), 2)

    def test_same_crs_layout(self):
        result = self.laid_out_rdd.reproject("EPSG:4326", layout=LayoutDefinition(self.extent, self.layout))
        new_metadata = result.layer_metadata

        layout_definition = LayoutDefinition(BaseTestClass.extent, BaseTestClass.layout)

        self.assertEqual(layout_definition, new_metadata.layout_definition)

    def test_integer_crs(self):
        result = self.laid_out_rdd.reproject(4326, layout=LayoutDefinition(self.extent, self.layout))
        new_metadata = result.layer_metadata

        layout_definition = LayoutDefinition(BaseTestClass.extent, BaseTestClass.layout)

        self.assertEqual(layout_definition, new_metadata.layout_definition)

    def test_same_crs_zoom(self):
        result = self.laid_out_rdd.reproject("EPSG:4326", layout=GlobalLayout())
        new_metadata = result.layer_metadata

        self.assertTrue("+datum=WGS84" in new_metadata.crs)

    def test_different_crs_layout(self):
        result = self.laid_out_rdd.reproject("EPSG:4324", layout=LayoutDefinition(self.extent, self.layout))
        new_metadata = result.layer_metadata

        self.assertEqual(self.expected_crs, new_metadata.crs)

    def test_different_crs_zoom(self):
        result = self.laid_out_rdd.reproject("EPSG:4324", layout=GlobalLayout())
        new_metadata = result.layer_metadata

        self.assertEqual(self.expected_crs, new_metadata.crs)

    def test_different_crs_float(self):
        result = self.laid_out_rdd.reproject("EPSG:4324", layout=LocalLayout(self.cols))
        new_metadata = result.layer_metadata

        self.assertEqual(self.expected_crs, new_metadata.crs)


if __name__ == "__main__":
    unittest.main()
