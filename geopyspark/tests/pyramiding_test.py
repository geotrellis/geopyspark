import os
import unittest
import rasterio

from geopyspark.constants import SPATIAL
from geopyspark.tests.python_test_utils import check_directory, geotiff_test_path
from geopyspark.geotrellis.tile_layer import (collect_metadata,
                                              collect_pyramid_metadata,
                                              tile_to_layout,
                                              pyramid)
from geopyspark.geotrellis.geotiff_rdd import geotiff_rdd
from geopyspark.tests.base_test_class import BaseTestClass


check_directory()


class PyramidingTest(BaseTestClass):
    dir_path = geotiff_test_path("all-ones.tif")
    rdd = geotiff_rdd(BaseTestClass.geopysc, SPATIAL, dir_path)

    def test_pyramid_building(self):
        (zoom, metadata) = collect_pyramid_metadata(BaseTestClass.geopysc,
                                                    SPATIAL,
                                                    self.rdd,
                                                    "EPSG:4326",
                                                    1024)

        laid_out = tile_to_layout(BaseTestClass.geopysc,
                                  SPATIAL,
                                  self.rdd,
                                  metadata)

        result = pyramid(BaseTestClass.geopysc,
                         rdd_type=SPATIAL,
                         base_raster_rdd=laid_out,
                         layer_metadata=metadata,
                         tile_size=1024,
                         start_zoom=1,
                         end_zoom=12)

        previous_layout_cols = None
        previous_layout_rows = None

        for x in result:
            layout_cols = x[2]['layoutDefinition']['tileLayout']['layoutCols']
            layout_rows = x[2]['layoutDefinition']['tileLayout']['layoutRows']

            if previous_layout_cols and previous_layout_rows:
                self.assertEqual(layout_cols*2, previous_layout_cols)
                self.assertEqual(layout_rows*2, previous_layout_rows)
            else:
                self.assertTrue(layout_cols % 2 == 0)
                self.assertTrue(layout_rows % 2 == 0)

            previous_layout_cols = layout_cols
            previous_layout_rows = layout_rows


if __name__ == "__main__":
    unittest.main()
