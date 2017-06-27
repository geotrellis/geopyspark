import unittest
from os import walk, path
import rasterio
import pytest

from geopyspark.geotrellis.constants import SPATIAL
from geopyspark.tests.python_test_utils import geotiff_test_path
from geopyspark.geotrellis.geotiff import get
from geopyspark.tests.base_test_class import BaseTestClass


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
                    rasterio_tiles.append({'cells': src.read(),
                                           'no_data_value': src.nodata})
                else:
                    for window in windows:
                        rasterio_tiles.append(
                            {'cells': src.read(window=window),
                             'no_data_value': src.nodata})

        return rasterio_tiles


class Singleband(GeoTiffIOTest, BaseTestClass):
    dir_path = geotiff_test_path("one-month-tiles/")

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def read_singleband_geotrellis(self, options=None):
        if options is None:
            result = get(BaseTestClass.pysc,
                         SPATIAL,
                         self.dir_path)
        else:
            result = get(BaseTestClass.pysc,
                         SPATIAL,
                         self.dir_path,
                         max_tile_size=256)

        return [tile[1] for tile in result.to_numpy_rdd().collect()]

    def test_whole_tiles(self):
        geotrellis_tiles = self.read_singleband_geotrellis()

        file_paths = self.get_filepaths(self.dir_path)
        rasterio_tiles = self.read_geotiff_rasterio(file_paths, False)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x.cells == y['cells']).all())
            self.assertEqual(x.no_data_value, y['no_data_value'])

    def windowed_result_checker(self, windowed_tiles):
        self.assertEqual(len(windowed_tiles), 4)

    def test_windowed_tiles(self):
        geotrellis_tiles = self.read_singleband_geotrellis(True)

        file_paths = self.get_filepaths(self.dir_path)
        rasterio_tiles = self.read_geotiff_rasterio(file_paths, True)

        self.windowed_result_checker(geotrellis_tiles)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x.cells == y['cells']).all())
            self.assertEqual(x.no_data_value, y['no_data_value'])

if __name__ == "__main__":
    unittest.main()
