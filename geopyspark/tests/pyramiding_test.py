import os
import unittest
import rasterio
import numpy as np
import pytest

from geopyspark.geotrellis import Extent, ProjectedExtent, TileLayout
from geopyspark.geotrellis.constants import SPATIAL, ZOOM
from geopyspark.geotrellis.rdd import RasterRDD
from geopyspark.tests.base_test_class import BaseTestClass


class PyramidingTest(BaseTestClass):

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_correct_base(self):
        arr = np.zeros((1, 16, 16))
        epsg_code = 3857
        extent = Extent(0.0, 0.0, 10.0, 10.0)

        tile = {'data': arr, 'no_data_value': False, 'data_type': 'FLOAT'}
        projected_extent = ProjectedExtent(extent, epsg_code)

        rdd = BaseTestClass.pysc.parallelize([(projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.pysc, SPATIAL, rdd)
        tile_layout = TileLayout(32, 32, 16, 16)
        new_extent = Extent(-20037508.342789244, -20037508.342789244, 20037508.342789244,
                            20037508.342789244)

        metadata = raster_rdd.collect_metadata(extent=new_extent, layout=tile_layout)
        laid_out = raster_rdd.tile_to_layout(metadata)

        result = laid_out.pyramid(start_zoom=5, end_zoom=1)

        self.pyramid_building_check(result)

    def test_no_start_zoom(self):
        arr = np.zeros((1, 16, 16))
        epsg_code = 3857
        extent = Extent(0.0, 0.0, 10.0, 10.0)

        tile = {'data': arr, 'no_data_value': False, 'data_type': 'FLOAT'}
        projected_extent = ProjectedExtent(extent, epsg_code)

        rdd = BaseTestClass.pysc.parallelize([(projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.pysc, SPATIAL, rdd)
        tile_layout = TileLayout(32, 32, 16, 16)
        new_extent = Extent(-20037508.342789244, -20037508.342789244, 20037508.342789244,
                            20037508.342789244)

        metadata = raster_rdd.collect_metadata(extent=new_extent, layout=tile_layout)
        laid_out = raster_rdd.tile_to_layout(metadata)
        reprojected = laid_out.reproject(3857, scheme=ZOOM)

        result = reprojected.pyramid(end_zoom=1)

        self.pyramid_building_check(result)

    def test_wrong_cols_and_rows(self):
        arr = np.zeros((1, 250, 250))
        epsg_code = 3857
        extent = Extent(0.0, 0.0, 10.0, 10.0)

        tile = {'data': arr, 'no_data_value': False, 'data_type': 'FLOAT'}
        projected_extent = ProjectedExtent(extent, epsg_code)

        rdd = BaseTestClass.pysc.parallelize([(projected_extent, tile)])

        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.pysc, SPATIAL, rdd)

        metadata = raster_rdd.collect_metadata(tile_size=250)
        laid_out = raster_rdd.tile_to_layout(metadata)

        with pytest.raises(ValueError):
            laid_out.pyramid(start_zoom=12, end_zoom=1)

    def pyramid_building_check(self, result):
        previous_layout_cols = None
        previous_layout_rows = None

        for x in result.levels.values():
            metadata = x.layer_metadata
            layout_cols = metadata.tile_layout.layoutCols
            layout_rows = metadata.tile_layout.layoutRows

            if previous_layout_cols and previous_layout_rows:
                self.assertEqual(layout_cols, previous_layout_cols*2)
                self.assertEqual(layout_rows, previous_layout_rows*2)
            else:
                self.assertTrue(layout_cols % 2 == 0)
                self.assertTrue(layout_rows % 2 == 0)

            previous_layout_cols = layout_cols
            previous_layout_rows = layout_rows


if __name__ == "__main__":
    unittest.main()
