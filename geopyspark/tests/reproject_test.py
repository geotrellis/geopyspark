import os
import unittest

from geopyspark.geotrellis.constants import ZOOM
from geopyspark.tests.base_test_class import BaseTestClass


class ReprojectTest(BaseTestClass):
    metadata = BaseTestClass.rdd.collect_metadata(extent=BaseTestClass.extent,
                                                  layout=BaseTestClass.layout)

    crs = metadata['crs']
    expected_crs = "+proj=longlat +ellps=WGS72 +towgs84=0,0,1.9,0,0,0.814,-0.38 +no_defs "

    laid_out_rdd = BaseTestClass.rdd.tile_to_layout(metadata)

    def test_same_crs_layout(self):
        result = self.laid_out_rdd.reproject("EPSG:4326", extent = self.extent, layout=self.layout)
        new_metadata = result.layer_metadata

        layout_definition = {'tileLayout': BaseTestClass.layout, 'extent': BaseTestClass.extent}

        self.assertDictEqual(layout_definition, new_metadata['layoutDefinition'])

    def test_same_crs_zoom(self):
        result = self.laid_out_rdd.reproject("EPSG:4326",
                                             scheme=ZOOM,
                                             tile_size=self.cols)
        new_metadata = result.layer_metadata

        self.assertTrue("+datum=WGS84" in new_metadata['crs'])

    def test_different_crs_layout(self):
        result = self.laid_out_rdd.reproject("EPSG:4324", extent=self.extent, layout=self.layout)
        new_metadata = result.layer_metadata

        self.assertEqual(self.expected_crs, new_metadata['crs'])

    def test_different_crs_zoom(self):
        result = self.laid_out_rdd.reproject("EPSG:4324",
                                             scheme=ZOOM,
                                             tile_size=self.cols)
        new_metadata = result.layer_metadata

        self.assertEqual(self.expected_crs, new_metadata['crs'])

    def test_different_crs_float(self):
        result = self.laid_out_rdd.reproject("EPSG:4324",
                                             tile_size=self.cols)
        new_metadata = result.layer_metadata

        self.assertEqual(self.expected_crs, new_metadata['crs'])


if __name__ == "__main__":
    unittest.main()
