from os import walk, path
import unittest
import rasterio

from geopyspark.tests.python_test_utils import check_directory, geotiff_test_path
from geopyspark.geotrellis.geotiff_rdd import S3GeoTiffRDD
from geopyspark.tests.base_test_class import BaseTestClass
from py4j.java_gateway import java_import


check_directory()


class S3GeoTiffIOTest(object):
    def get_filepaths(self, dir_path):
        files = []

        for (fd, dn, filenames) in walk(dir_path):
            files.extend(filenames)

        return [path.join(dir_path, x) for x in files]

    def read_geotiff_rasterio(self, paths, windowed):
        rasterio_tiles = []

        windows = [((0, 256), (0, 256)),
                   ((256, 512), (0, 256)),
                   ((0, 256), (256, 512)),
                   ((256, 512), (256, 512))]

        for f in paths:
            with rasterio.open(f) as src:
                if not windowed:
                    rasterio_tiles.append({'data': src.read(),
                                           'no_data_value': src.nodata})
                else:
                    for window in windows:
                        rasterio_tiles.append(
                            {'data': src.read(window=window),
                             'no_data_value': src.nodata})

        return rasterio_tiles


class Singleband(S3GeoTiffIOTest, BaseTestClass):
    java_import(BaseTestClass.geopysc._jvm,
                "geopyspark.geotrellis.testkit.MockS3ClientWrapper")

    mock_wrapper = BaseTestClass.geopysc._jvm.MockS3ClientWrapper
    client = mock_wrapper.mockClient()

    s3_geotiff = S3GeoTiffRDD(BaseTestClass.geopysc)

    key = "one-month-tiles/test-200506000000_0_0.tif"
    bucket = "test"
    file_path = geotiff_test_path(key)

    in_file = open(file_path, "rb")
    data = in_file.read()
    in_file.close()

    options = {"s3Client": "mock"}

    def read_singleband_geotrellis(self, opt=options):
        self.client.putObject(self.bucket, self.key, self.data)
        result = self.s3_geotiff.get_rdd("spatial",
                                         "singleband",
                                         self.bucket,
                                         self.key,
                                         opt)

        return [tile[1] for tile in result.collect()]

    def test_whole_tiles(self):

        geotrellis_tiles = self.read_singleband_geotrellis()
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], False)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x['data'] == y['data']).all())
            self.assertEqual(x['no_data_value'], y['no_data_value'])

    def windowed_result_checker(self, windowed_tiles):
        self.assertEqual(len(windowed_tiles), 4)

    def test_windowed_tiles(self):
        geotrellis_tiles = self.read_singleband_geotrellis({'s3Client': 'mock', 'maxTileSize': 256})
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], True)

        self.windowed_result_checker(geotrellis_tiles)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x['data'] == y['data']).all())
            self.assertEqual(x['no_data_value'], y['no_data_value'])


class Multiband(S3GeoTiffIOTest, BaseTestClass):
    java_import(BaseTestClass.geopysc._jvm,
                "geopyspark.geotrellis.testkit.MockS3ClientWrapper")

    mock_wrapper = BaseTestClass.geopysc._jvm.MockS3ClientWrapper
    client = mock_wrapper.mockClient()

    s3_geotiff = S3GeoTiffRDD(BaseTestClass.geopysc)

    key = "one-month-tiles-multiband/result.tif"
    bucket = "test"
    file_path = geotiff_test_path(key)
    options = {"s3Client": "mock"}

    in_file = open(file_path, "rb")
    data = in_file.read()
    in_file.close()

    def read_multiband_geotrellis(self, opt=options):
        self.client.putObject(self.bucket, self.key, self.data)
        result = self.s3_geotiff.get_rdd("spatial",
                                         "multiband",
                                         self.bucket,
                                         self.key,
                                         opt)

        return [tile[1] for tile in result.collect()]

    def test_whole_tiles(self):
        geotrellis_tiles = self.read_multiband_geotrellis()
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], False)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x['data'] == y['data']).all())

    def windowed_result_checker(self, windowed_tiles):
        self.assertEqual(len(windowed_tiles), 4)

    def test_windowed_tiles(self):
        geotrellis_tiles = self.read_multiband_geotrellis({"s3Client": "mock", "maxTileSize": 256})
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], True)

        self.windowed_result_checker(geotrellis_tiles)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x['data'] == y['data']).all())


if __name__ == "__main__":
    unittest.main()
