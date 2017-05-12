import os
import unittest
import rasterio

from geopyspark.geotrellis.constants import SPATIAL
from geopyspark.geotrellis.rdd import RasterRDD
from geopyspark.tests.base_test_class import BaseTestClass


class TileLayerMetadataTest(BaseTestClass):
    extent = BaseTestClass.extent
    layout = BaseTestClass.layout
    rdd = BaseTestClass.rdd
    projected_extent = BaseTestClass.projected_extent
    cols = BaseTestClass.cols

    def test_collection_avro_rdd(self):
        result = self.rdd.collect_metadata(self.extent, self.layout)

        self.assertDictEqual(result['extent'], self.extent)
        self.assertDictEqual(result['layoutDefinition']['extent'], self.extent)
        self.assertDictEqual(result['layoutDefinition']['tileLayout'], self.layout)

    def test_collection_python_rdd(self):
        data = rasterio.open(self.dir_path)
        tile_dict = {'data': data.read(), 'no_data_value': data.nodata}

        rasterio_rdd = self.geopysc.pysc.parallelize([(self.projected_extent, tile_dict)])
        raster_rdd = RasterRDD.from_numpy_rdd(self.geopysc, SPATIAL, rasterio_rdd)

        result = raster_rdd.collect_metadata(extent=self.extent, layout=self.layout)

        self.assertDictEqual(result['extent'], self.extent)
        self.assertDictEqual(result['layoutDefinition']['extent'], self.extent)
        self.assertDictEqual(result['layoutDefinition']['tileLayout'], self.layout)

    def test_collection_floating(self):
        result = self.rdd.collect_metadata(tile_size=self.cols)

        self.assertDictEqual(result['extent'], self.extent)
        self.assertDictEqual(result['layoutDefinition']['extent'], self.extent)
        self.assertDictEqual(result['layoutDefinition']['tileLayout'], self.layout)


if __name__ == "__main__":
    unittest.main()
