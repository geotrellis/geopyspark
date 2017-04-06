import os
import unittest

from geopyspark.constants import SPATIAL
from geopyspark.tests.python_test_utils import check_directory, geotiff_test_path
from geopyspark.geotrellis.tile_layer import reproject_to_layout, collect_metadata, tile_to_layout
from geopyspark.geotrellis.geotiff_rdd import geotiff_rdd
from geopyspark.tests.base_test_class import BaseTestClass


check_directory()


class ReprojectTest(BaseTestClass):
    dir_path = geotiff_test_path("all-ones.tif")

    rdd = geotiff_rdd(BaseTestClass.geopysc, SPATIAL, dir_path)
    value = rdd.collect()[0]

    extent = value[0]['extent']

    expected_tile = value[1]['data']

    (_, expected_rows, expected_cols) = expected_tile.shape

    layout = {
        "layoutCols": 1,
        "layoutRows": 1,
        "tileCols": expected_cols,
        "tileRows": expected_rows
    }

    metadata = collect_metadata(BaseTestClass.geopysc,
                                SPATIAL,
                                rdd,
                                extent,
                                layout)
    crs = metadata['crs']

    laid_out_rdd = tile_to_layout(BaseTestClass.geopysc,
                                  SPATIAL,
                                  rdd,
                                  metadata)

    def test_same_crs_layout(self):
        (_, _, new_metadata) = reproject_to_layout(BaseTestClass.geopysc,
                                                   SPATIAL,
                                                   self.laid_out_rdd,
                                                   self.metadata,
                                                   "EPSG:4326",
                                                   layout_extent=self.extent,
                                                   tile_layout=self.layout)

        layout_definition = {'tileLayout': self.layout, 'extent': self.extent}

        self.assertDictEqual(layout_definition, new_metadata['layoutDefinition'])

    def test_same_crs_zoom(self):
        (_, new_rdd, new_metadata) = reproject_to_layout(BaseTestClass.geopysc,
                                                         SPATIAL,
                                                         self.laid_out_rdd,
                                                         self.metadata,
                                                         "EPSG:4326",
                                                         tile_size=self.expected_cols,
                                                         resolution_threshold=0.1)

        actual_tile = new_rdd.first()[1]['data']
        (_, actual_rows, actual_cols) = actual_tile.shape

        self.assertTrue(self.expected_cols >= actual_cols)
        self.assertTrue(self.expected_rows >= actual_rows)

    def test_different_crs_layout(self):
        (_, new_rdd, new_metadata) = reproject_to_layout(BaseTestClass.geopysc,
                                                         SPATIAL,
                                                         self.laid_out_rdd,
                                                         self.metadata,
                                                         "EPSG:4324",
                                                         layout_extent=self.extent,
                                                         tile_layout=self.layout)

        actual_tile = new_rdd.first()[1]['data']
        (_, actual_rows, actual_cols) = actual_tile.shape

        self.assertTrue(self.expected_cols >= actual_cols)
        self.assertTrue(self.expected_rows >= actual_rows)

    def test_different_crs_zoom(self):
        (_, new_rdd, new_metadata) = reproject_to_layout(BaseTestClass.geopysc,
                                                         SPATIAL,
                                                         self.laid_out_rdd,
                                                         self.metadata,
                                                         "EPSG:4324",
                                                         tile_size=500,
                                                         resolution_threshold=0.1)

        actual_tile = new_rdd.first()[1]['data']
        (_, actual_rows, actual_cols) = actual_tile.shape

        self.assertTrue(self.expected_cols >= actual_cols)
        self.assertTrue(self.expected_rows >= actual_rows)

    def test_different_crs_float(self):
        (_, new_rdd, new_metadata) = reproject_to_layout(BaseTestClass.geopysc,
                                                         SPATIAL,
                                                         self.laid_out_rdd,
                                                         self.metadata,
                                                         "EPSG:4324",
                                                         tile_size=500)

        actual_tile = new_rdd.first()[1]['data']
        (_, actual_rows, actual_cols) = actual_tile.shape

        self.assertTrue(self.expected_cols >= actual_cols)
        self.assertTrue(self.expected_rows >= actual_rows)


if __name__ == "__main__":
    unittest.main()
