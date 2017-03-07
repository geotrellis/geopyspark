from geopyspark.tests.python_test_utils import *
add_spark_path()
check_directory()

from geopyspark.geotrellis.geotiff_rdd import HadoopGeoTiffRDD
from geopyspark.geopycontext import GeoPyContext
from geopyspark.tests.base_test_class import BaseTestClass
from os import walk, path

import rasterio
import unittest
import pytest
import os


class GeoTiffIOTest(object):
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


class Singleband(GeoTiffIOTest, BaseTestClass):
    hadoop_geotiff = HadoopGeoTiffRDD(BaseTestClass.geopysc)

    dir_path = geotiff_test_path("one-month-tiles/")
    options = {'maxTileSize': 256}

    def read_singleband_geotrellis(self, options=None):
        if options is None:
            result = self.hadoop_geotiff.get_rdd("spatial", "singleband", self.dir_path)
        else:
            result = self.hadoop_geotiff.get_rdd("spatial", "singleband", self.dir_path, options)

        return [tile[1] for tile in result.collect()]

    def test_whole_tiles(self):
        geotrellis_tiles = self.read_singleband_geotrellis()

        file_paths = self.get_filepaths(self.dir_path)
        rasterio_tiles = self.read_geotiff_rasterio(file_paths, False)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x == y).all())

    def windowed_result_checker(self, windowed_tiles):
        self.assertEqual(len(windowed_tiles), 24)

    def test_windowed_tiles(self):
        geotrellis_tiles = self.read_singleband_geotrellis(self.options)

        file_paths = self.get_filepaths(self.dir_path)
        rasterio_tiles = self.read_geotiff_rasterio(file_paths, True)

        self.windowed_result_checker(geotrellis_tiles)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x == y).all())


class Multiband(GeoTiffIOTest, BaseTestClass):
    hadoop_geotiff = HadoopGeoTiffRDD(BaseTestClass.geopysc)
    dir_path = geotiff_test_path("one-month-tiles-multiband/")
    options = {'maxTileSize': 256}

    def read_multiband_geotrellis(self, options=None):
        if options is None:
            result = self.hadoop_geotiff.get_rdd("spatial", "multiband", self.dir_path)
        else:
            result = self.hadoop_geotiff.get_rdd("spatial", "multiband", self.dir_path, options)

        return [tile[1] for tile in result.collect()]

    def test_whole_tiles(self):
        geotrellis_tiles = self.read_multiband_geotrellis()

        file_paths = self.get_filepaths(self.dir_path)
        rasterio_tiles = self.read_geotiff_rasterio(file_paths, False)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x == y).all())

    def windowed_result_checker(self, windowed_tiles):
        self.assertEqual(len(windowed_tiles), 4)

    def test_windowed_tiles(self):

        geotrellis_tiles = self.read_multiband_geotrellis(options=self.options)

        file_paths = self.get_filepaths(self.dir_path)
        rasterio_tiles = self.read_geotiff_rasterio(file_paths, True)

        self.windowed_result_checker(geotrellis_tiles)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x == y).all())


if __name__ == "__main__":
    unittest.main()
