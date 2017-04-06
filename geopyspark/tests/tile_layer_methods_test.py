import os
import unittest
import rasterio

from geopyspark.constants import SPATIAL
from geopyspark.tests.python_test_utils import check_directory, geotiff_test_path
from geopyspark.geotrellis.tile_layer import (collect_metadata,
                                              cut_tiles,
                                              merge_tiles,
                                              tile_to_layout)
from geopyspark.geotrellis.geotiff_rdd import geotiff_rdd
from geopyspark.tests.base_test_class import BaseTestClass


check_directory()


class TileLayerMethodsTest(BaseTestClass):
    dir_path = geotiff_test_path("all-ones.tif")
    hadoop_rdd = geotiff_rdd(BaseTestClass.geopysc, SPATIAL, dir_path)

    data = rasterio.open(dir_path)
    no_data = data.nodata
    tile = data.read()
    tile_dict = {'data': tile, 'no_data_value': no_data}

    value = hadoop_rdd.collect()[0]

    rasterio_rdd = BaseTestClass.geopysc.pysc.parallelize([(value[0], tile_dict)])

    extent = value[0]['extent']

    (_, _rows, _cols) = value[1]['data'].shape

    layout = {
        "layoutCols": 1,
        "layoutRows": 1,
        "tileCols": _cols,
        "tileRows": _rows
    }

    metadata = collect_metadata(BaseTestClass.geopysc,
                                SPATIAL,
                                hadoop_rdd,
                                extent,
                                layout)

    def test_cut_tiles_hadoop(self):
        result = cut_tiles(BaseTestClass.geopysc,
                           SPATIAL,
                           self.hadoop_rdd,
                           self.metadata)

        (key_bounds, tile) = result.collect()[0]

        self.assertEqual([0, 0], [key_bounds['col'], key_bounds['row']])
        self.assertTrue((self.value[1]['data'] == tile['data']).all())

    def test_cut_tiles_rasterio(self):
        result = cut_tiles(BaseTestClass.geopysc,
                           SPATIAL,
                           self.rasterio_rdd,
                           self.metadata)

        (key_bounds, tile) = result.collect()[0]

        self.assertEqual([0, 0], [key_bounds['col'], key_bounds['row']])
        self.assertTrue((self.value[1]['data'] == tile['data']).all())

    def test_tile_to_layout_hadoop(self):
        result = tile_to_layout(BaseTestClass.geopysc,
                                SPATIAL,
                                self.hadoop_rdd,
                                self.metadata)

        (key_bounds, tile) = result.collect()[0]

        self.assertEqual([0, 0], [key_bounds['col'], key_bounds['row']])
        self.assertTrue((self.value[1]['data'] == tile['data']).all())

    def test_tile_to_layout_rasterio(self):
        result = tile_to_layout(BaseTestClass.geopysc,
                                SPATIAL,
                                self.rasterio_rdd,
                                self.metadata)

        (key_bounds, tile) = result.collect()[0]

        self.assertEqual([0, 0], [key_bounds['col'], key_bounds['row']])
        self.assertTrue((self.value[1]['data'] == tile['data']).all())

    def test_merge(self):
        result = merge_tiles(BaseTestClass.geopysc,
                             SPATIAL,
                             self.rasterio_rdd,
                             self.hadoop_rdd)

        tile = result.collect()[0][1]

        self.assertTrue((self.value[1]['data'] == tile['data']).all())


if __name__ == "__main__":
    unittest.main()
