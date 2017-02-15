from geopyspark.tests.python_test_utils import *
add_spark_path()
check_directory()

from pyspark import SparkContext
from geopyspark.geotrellis.geotiff_rdd import S3GeoTiffRDD
from py4j.java_gateway import java_import
from os import walk, path

import rasterio
import unittest
import pytest


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
                    rasterio_tiles.append(src.read())
                else:
                    for window in windows:
                        rasterio_tiles.append(src.read(window=window))

        return rasterio_tiles


class Singleband(S3GeoTiffIOTest, unittest.TestCase):
    def setUp(self):
        self.pysc = SparkContext(master="local[*]", appName="s3-singlebandgeotiff-test")

        java_import(self.pysc._gateway.jvm,
                "geopyspark.geotrellis.testkit.MockS3ClientWrapper")

        self.mock_wrapper = self.pysc._gateway.jvm.MockS3ClientWrapper
        self.client = self.mock_wrapper.mockClient()

        self.s3_geotiff = S3GeoTiffRDD(self.pysc)

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        self.pysc.stop()
        self.pysc._gateway.close()

    key = "one-month-tiles/test-200506000000_0_0.tif"
    bucket = "test"
    file_path = geotiff_test_path(key)

    in_file = open(file_path, "rb")
    data = in_file.read()
    in_file.close()

    options = {"s3Client": "mock"}

    def read_singleband_geotrellis(self, opt=options):
        self.client.putObject(self.bucket, self.key, self.data)
        result = self.s3_geotiff.get_spatial(self.bucket, self.key, opt)[0]

        return [tile[1] for tile in result.collect()]

    def test_whole_tiles(self):

        geotrellis_tiles = self.read_singleband_geotrellis()
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], False)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x == y).all())

    def windowed_result_checker(self, windowed_tiles):
        self.assertEqual(len(windowed_tiles), 4)

    def test_windowed_tiles(self):
        geotrellis_tiles = self.read_singleband_geotrellis({'s3Client': 'mock', 'maxTileSize': 256})
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], True)

        self.windowed_result_checker(geotrellis_tiles)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x == y).all())


class Multiband(S3GeoTiffIOTest, unittest.TestCase):
    def setUp(self):
        self.pysc = SparkContext(master="local[*]", appName="s3-multibandgeotiff-test")

        java_import(self.pysc._gateway.jvm,
                "geopyspark.geotrellis.testkit.MockS3ClientWrapper")

        self.mock_wrapper = self.pysc._gateway.jvm.MockS3ClientWrapper
        self.client = self.mock_wrapper.mockClient()

        self.s3_geotiff = S3GeoTiffRDD(self.pysc)

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        self.pysc.stop()
        self.pysc._gateway.close()

    key = "one-month-tiles-multiband/result.tif"
    bucket = "test"
    file_path = geotiff_test_path(key)
    options = {"s3Client": "mock"}

    in_file = open(file_path, "rb")
    data = in_file.read()
    in_file.close()

    def read_multiband_geotrellis(self, opt=options):
        self.client.putObject(self.bucket, self.key, self.data)
        result = self.s3_geotiff.get_spatial_multiband(self.bucket, self.key, opt)[0]

        return [tile[1] for tile in result.collect()]

    def test_whole_tiles(self):
        geotrellis_tiles = self.read_multiband_geotrellis()
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], False)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x == y).all())

    def windowed_result_checker(self, windowed_tiles):
        self.assertEqual(len(windowed_tiles), 4)

    def test_windowed_tiles(self):
        geotrellis_tiles = self.read_multiband_geotrellis({"s3Client": "mock", "maxTileSize": 256})
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], True)

        self.windowed_result_checker(geotrellis_tiles)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x == y).all())


if __name__ == "__main__":
    unittest.main()
