import os
import unittest
import rasterio

from geopyspark.tests.python_test_utils import check_directory, geotiff_test_path
from geopyspark.geotrellis.tile_layer_methods import TileLayerMethods
from geopyspark.geotrellis.geotiff_rdd import HadoopGeoTiffRDD
from geopyspark.tests.base_test_class import BaseTestClass


check_directory()


class TileLayerMetadataTest(BaseTestClass):
    metadata = TileLayerMethods(BaseTestClass.geopysc)
    hadoop_geotiff = HadoopGeoTiffRDD(BaseTestClass.geopysc)

    dir_path = geotiff_test_path("all-ones.tif")
    options = {'maxTileSize': 256}

    rdd = hadoop_geotiff.get_rdd("spatial", "singleband", dir_path)
    value = rdd.collect()[0]

    projected_extent = value[0]
    extent = projected_extent['extent']

    (rows, cols) = value[1]['data'].shape

    layout = {
        "layoutCols": 1,
        "layoutRows": 1,
        "tileCols": cols,
        "tileRows": rows
    }

    actual = [[extent, layout], extent]

    def check_results(self, actual, expected):
        if isinstance(actual, list) and isinstance(expected, list):
            for x,y in zip(actual, expected):
                self.check_results(x, y)
        elif isinstance(actual, dict) and isinstance(expected, dict):
            self.assertDictEqual(actual, expected)
        else:
            self.assertEqual(actual, expected)

    def test_collection_avro_rdd(self):
        result = self.metadata.collect_metadata("spatial",
                                                "singleband",
                                                self.rdd,
                                                self.extent,
                                                self.layout,
                                                epsg_code=self.value[0]['epsg'])

        expected = [[result['layoutDefinition']['extent'],
                     result['layoutDefinition']['tileLayout']],
                    result['extent']]

        self.check_results(self.actual, expected)

    def test_collection_python_rdd(self):
        data = rasterio.open(self.dir_path)
        tile_dict = {'data': data.read(), 'no_data_value': data.nodata}
        rasterio_rdd = self.geopysc.pysc.parallelize([(self.projected_extent, tile_dict)])

        result = self.metadata.collect_metadata("spatial",
                                                "singleband",
                                                rasterio_rdd,
                                                self.extent,
                                                self.layout,
                                                epsg_code=self.value[0]['epsg'])

        expected = [[result['layoutDefinition']['extent'],
                     result['layoutDefinition']['tileLayout']],
                    result['extent']]

        self.check_results(self.actual, expected)


if __name__ == "__main__":
    unittest.main()
