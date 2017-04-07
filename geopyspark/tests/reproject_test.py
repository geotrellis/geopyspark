import os
import unittest

from geopyspark.constants import SPATIAL, ZOOM
from geopyspark.tests.python_test_utils import check_directory, geotiff_test_path
from geopyspark.geotrellis.geotiff_rdd import geotiff_rdd
from geopyspark.tests.base_test_class import BaseTestClass


check_directory()


class ReprojectTest(BaseTestClass):
    dir_path = geotiff_test_path("all-ones.tif")

    rdd = geotiff_rdd(BaseTestClass.geopysc, SPATIAL, dir_path)
    value = rdd.to_numpy_rdd().collect()[0]

    extent = value[0]['extent']

    expected_tile = value[1]['data']

    (_, expected_rows, expected_cols) = expected_tile.shape

    layout = {
        "layoutCols": 1,
        "layoutRows": 1,
        "tileCols": expected_cols,
        "tileRows": expected_rows
    }

    metadata = rdd.collect_metadata(extent=extent, layout=layout)

    crs = metadata['crs']
    expected_crs = "+proj=longlat +ellps=WGS72 +towgs84=0,0,1.9,0,0,0.814,-0.38 +no_defs "

    laid_out_rdd = rdd.tile_to_layout(metadata)

    def test_same_crs_layout(self):
        result = self.laid_out_rdd.reproject("EPSG:4326", extent = self.extent, layout=self.layout)
        new_metadata = result.layer_metadata

        layout_definition = {'tileLayout': self.layout, 'extent': self.extent}

        self.assertDictEqual(layout_definition, new_metadata['layoutDefinition'])

    def test_same_crs_zoom(self):
        result = self.laid_out_rdd.reproject("EPSG:4326",
                                             scheme=ZOOM,
                                             tile_size=self.expected_cols)
        new_metadata = result.layer_metadata

        self.assertTrue("+datum=WGS84" in new_metadata['crs'])

    def test_different_crs_layout(self):
        result = self.laid_out_rdd.reproject("EPSG:4324", extent=self.extent, layout=self.layout)
        new_metadata = result.layer_metadata

        self.assertEqual(self.expected_crs, new_metadata['crs'])

    def test_different_crs_zoom(self):
        result = self.laid_out_rdd.reproject("EPSG:4324",
                                             scheme=ZOOM,
                                             tile_size=self.expected_cols)
        new_metadata = result.layer_metadata

        self.assertEqual(self.expected_crs, new_metadata['crs'])

    def test_different_crs_float(self):
        result = self.laid_out_rdd.reproject("EPSG:4324",
                                             tile_size=self.expected_cols)
        new_metadata = result.layer_metadata

        self.assertEqual(self.expected_crs, new_metadata['crs'])


if __name__ == "__main__":
    unittest.main()
