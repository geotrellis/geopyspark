import os
import unittest
import rasterio

from geopyspark.tests.python_test_utils import check_directory, geotiff_test_path
from geopyspark.geotrellis.tile_layer_methods import TileLayerMethods
from geopyspark.geotrellis.geotiff_rdd import HadoopGeoTiffRDD
from geopyspark.tests.base_test_class import BaseTestClass


check_directory()


class TileLayerMethodsTest(BaseTestClass):
    methods = TileLayerMethods(BaseTestClass.geopysc)
    hadoop_geotiff = HadoopGeoTiffRDD(BaseTestClass.geopysc)

    dir_path = geotiff_test_path("all-ones.tif")
    hadoop_rdd = hadoop_geotiff.get_rdd("spatial", "singleband", dir_path)

    data = rasterio.open(dir_path)
    no_data = data.nodata
    tile = data.read(1)
    tile_dict = {'data': tile, 'no_data_value': no_data}

    value = hadoop_rdd.collect()[0]

    rasterio_rdd = BaseTestClass.geopysc.pysc.parallelize([(value[0], tile_dict)])

    extent = value[0]['extent']

    (_rows, _cols) = value[1]['data'].shape

    layout = {
        "layoutCols": 1,
        "layoutRows": 1,
        "tileCols": _cols,
        "tileRows": _rows
    }

    metadata = methods.collect_metadata("spatial",
                                        "singleband",
                                        hadoop_rdd,
                                        extent,
                                        layout,
                                        epsg_code=value[0]['epsg'])

    def test_cut_tiles_hadoop(self):
        result = self.methods.cut_tiles("spatial",
                                        "singleband",
                                        self.hadoop_rdd,
                                        self.metadata)

        (key_bounds, tile) = result.collect()[0]

        self.assertEqual([0, 0], [key_bounds['col'], key_bounds['row']])
        self.assertTrue((self.value[1]['data'] == tile['data']).all())

    def test_cut_tiles_rasterio(self):
        result = self.methods.cut_tiles("spatial",
                                        "singleband",
                                        self.rasterio_rdd,
                                        self.metadata)

        (key_bounds, tile) = result.collect()[0]

        self.assertEqual([0, 0], [key_bounds['col'], key_bounds['row']])
        self.assertTrue((self.value[1]['data'] == tile['data']).all())

    def test_tile_to_layout_hadoop(self):
        result = self.methods.tile_to_layout("spatial",
                                             "singleband",
                                             self.hadoop_rdd,
                                             self.metadata)

        (key_bounds, tile) = result.collect()[0]

        self.assertEqual([0, 0], [key_bounds['col'], key_bounds['row']])
        self.assertTrue((self.value[1]['data'] == tile['data']).all())

    def test_tile_to_layout_rasterio(self):
        result = self.methods.tile_to_layout("spatial",
                                             "singleband",
                                             self.rasterio_rdd,
                                             self.metadata)

        (key_bounds, tile) = result.collect()[0]

        self.assertEqual([0, 0], [key_bounds['col'], key_bounds['row']])
        self.assertTrue((self.value[1]['data'] == tile['data']).all())

    def test_merge(self):
        result = self.methods.merge("spatial",
                                    "singleband",
                                    self.rasterio_rdd,
                                    self.hadoop_rdd)

        tile = result.collect()[0][1]

        self.assertTrue((self.value[1]['data'] == tile['data']).all())


if __name__ == "__main__":
    unittest.main()
