import os
import unittest
import rasterio
import numpy as np
import pytest

from geopyspark.geotrellis import Extent, ProjectedExtent, TileLayout, Tile, GlobalLayout
from geopyspark.geotrellis.constants import LayerType, LayoutScheme
from geopyspark.geotrellis.layer import Pyramid, RasterLayer
from geopyspark.tests.base_test_class import BaseTestClass


class PyramidingTest(BaseTestClass):

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_non_power_of_two(self):
        arr = np.zeros((1, 17, 17))
        epsg_code = 3857
        extent = Extent(0.0, 0.0, 10.0, 10.0)

        tile = Tile(arr, 'FLOAT', False)
        projected_extent = ProjectedExtent(extent, epsg_code)

        rdd = BaseTestClass.pysc.parallelize([(projected_extent, tile)])
        raster_rdd = RasterLayer.from_numpy_rdd(BaseTestClass.pysc, LayerType.SPATIAL, rdd)
        tile_layout = TileLayout(1, 1, 17, 17)

        metadata = raster_rdd.collect_metadata(tile_size=17, crs=3857)
        laid_out = raster_rdd.tile_to_layout(metadata)

        result = laid_out.pyramid_non_power_of_two(col_power=10, row_power=10, end_zoom=2, start_zoom=9)

        self.assertTrue(isinstance(result, Pyramid))
        self.assertEqual(result.levels[2].layer_metadata.tile_layout.tileCols, 1<<10)
        self.assertEqual(result.levels[2].layer_metadata.tile_layout.tileRows, 1<<10)
        self.assertEqual(result.levels[9].layer_metadata.tile_layout.tileCols, 1<<10)
        self.assertEqual(result.levels[9].layer_metadata.tile_layout.tileRows, 1<<10)

    def test_correct_base(self):
        arr = np.zeros((1, 16, 16))
        epsg_code = 3857
        extent = Extent(0.0, 0.0, 10.0, 10.0)

        tile = Tile(arr, 'FLOAT', False)
        projected_extent = ProjectedExtent(extent, epsg_code)

        rdd = BaseTestClass.pysc.parallelize([(projected_extent, tile)])
        raster_rdd = RasterLayer.from_numpy_rdd(BaseTestClass.pysc, LayerType.SPATIAL, rdd)
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

        tile = Tile(arr, 'FLOAT', None)
        projected_extent = ProjectedExtent(extent, epsg_code)

        rdd = BaseTestClass.pysc.parallelize([(projected_extent, tile)])
        raster_rdd = RasterLayer.from_numpy_rdd(BaseTestClass.pysc, LayerType.SPATIAL, rdd)
        tile_layout = TileLayout(32, 32, 16, 16)
        new_extent = Extent(-20037508.342789244, -20037508.342789244, 20037508.342789244,
                            20037508.342789244)

        metadata = raster_rdd.collect_metadata(extent=new_extent, layout=tile_layout)
        laid_out = raster_rdd.tile_to_layout(metadata)
        reprojected = laid_out.reproject(3857, layout=GlobalLayout(16, laid_out.zoom_level, 0.1))

        result = reprojected.pyramid(end_zoom=1)

        #self.pyramid_building_check(result)

    def test_wrong_cols_and_rows(self):
        arr = np.zeros((1, 250, 250))
        epsg_code = 3857
        extent = Extent(0.0, 0.0, 10.0, 10.0)

        tile = Tile(arr, 'FLOAT', None)
        projected_extent = ProjectedExtent(extent, epsg_code)

        rdd = BaseTestClass.pysc.parallelize([(projected_extent, tile)])

        raster_rdd = RasterLayer.from_numpy_rdd(BaseTestClass.pysc, LayerType.SPATIAL, rdd)

        metadata = raster_rdd.collect_metadata(tile_size=250)
        laid_out = raster_rdd.tile_to_layout(metadata)

        with pytest.raises(ValueError):
            laid_out.pyramid(start_zoom=12, end_zoom=1)

    def test_pyramid_class(self):
        arr = np.zeros((1, 16, 16))
        epsg_code = 3857
        extent = Extent(0.0, 0.0, 10.0, 10.0)

        tile = Tile(arr, 'FLOAT', False)
        projected_extent = ProjectedExtent(extent, epsg_code)

        rdd = BaseTestClass.pysc.parallelize([(projected_extent, tile)])
        raster_rdd = RasterLayer.from_numpy_rdd(BaseTestClass.pysc, LayerType.SPATIAL, rdd)
        tile_layout = TileLayout(1, 1, 16, 16)

        metadata = raster_rdd.collect_metadata(tile_size=16)
        laid_out = raster_rdd.tile_to_layout(metadata)
        reprojected = laid_out.reproject(3857, layout=GlobalLayout(16, 12, 0.1))

        result = reprojected.pyramid(end_zoom=1, start_zoom=12)
        hist = result.get_histogram()

        self.assertEqual(result.max_zoom, 12)
        self.assertTrue(set(result.levels.keys()).issuperset(range(1, 13)))
        self.assertEqual(hist.mean(), 0.0)
        self.assertEqual(hist.min_max(), (0.0, 0.0))

    def pyramid_building_check(self, result):
        previous_layout_cols = None
        previous_layout_rows = None

        values = sorted(list(result.levels.items()), reverse=True, key=lambda tup: tup[0])

        for x in values:
            metadata = x[1].layer_metadata
            layout_cols = metadata.tile_layout.layoutCols
            layout_rows = metadata.tile_layout.layoutRows

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
