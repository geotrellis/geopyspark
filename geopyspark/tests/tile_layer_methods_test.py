from geopyspark.tests.python_test_utils import *
add_spark_path()
check_directory()

from pyspark import SparkContext
from geopyspark.geotrellis.tile_layer_methods import TileLayerMethods
from geopyspark.geotrellis.geotiff_rdd import HadoopGeoTiffRDD
from py4j.java_gateway import java_import
from geopyspark.avroserializer import AvroSerializer

import unittest
import pytest
import numpy as np


class TileLayerMetadataTest(unittest.TestCase):
    def setUp(self):
        self.pysc = SparkContext(master="local[*]", appName="metadata-test")
        self.methods = TileLayerMethods(self.pysc)
        self.hadoop_geotiff = HadoopGeoTiffRDD(self.pysc)

        self.dir_path = geotiff_test_path("all-ones.tif")
        (self.rdd, self.schema) = self.hadoop_geotiff.get_spatial(self.dir_path)

        self.value = self.rdd.collect()[0]

        _projected_extent = self.value[0]
        _old_extent = _projected_extent.extent

        self.new_extent = {
            "xmin": _old_extent.xmin,
            "ymin": _old_extent.ymin,
            "xmax": _old_extent.xmax,
            "ymax": _old_extent.ymax
        }

        (_rows, _cols) = self.value[1].shape

        self.layout = {
            "layoutCols": 1,
            "layoutRows": 1,
            "tileCols": _cols,
            "tileRows": _rows
        }

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        self.pysc.stop()
        self.pysc._gateway.close()

    def test_metadat_collection(self):

        result = self.methods.collect_metadata(self.rdd,
                                               self.schema,
                                               self.new_extent,
                                               self.layout,
                                               epsg_code=self.value[0].epsg_code)

        returned_layout_extent = result['layout'][0]
        layout_java_object = result['layout'][1]

        returned_extent = {
            'xmin': returned_layout_extent['xmin'],
            'ymin': returned_layout_extent['ymin'],
            'xmax': returned_layout_extent['xmax'],
            'ymax': returned_layout_extent['ymax']
        }

        returned_layout = {
            'layoutCols': layout_java_object['layoutCols'],
            'layoutRows': layout_java_object['layoutRows'],
            'tileCols': layout_java_object['tileCols'],
            'tileRows': layout_java_object['tileRows']
        }

        self.assertEqual(self.value[1].dtype.name, result['cellType'])
        self.assertDictEqual(self.layout, returned_layout)
        self.assertDictEqual(self.new_extent, returned_extent)

    def test_cut_tiles(self):
        metadata = self.methods.collect_metadata(self.rdd,
                                                 self.schema,
                                                 self.new_extent,
                                                 self.layout,
                                                 epsg_code=self.value[0].epsg_code)

        result = self.methods.cut_tiles(self.rdd,
                                               self.schema,
                                               metadata)

        (key_bounds, tile) = result[0].collect()[0]

        self.assertEqual([0,0], [key_bounds.col, key_bounds.row])
        self.assertTrue((self.value[1] == tile).all())



if __name__ == "__main__":
    unittest.main()
