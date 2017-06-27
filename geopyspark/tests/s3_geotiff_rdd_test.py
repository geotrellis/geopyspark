from os import walk, path
import unittest
import rasterio
import pytest

from geopyspark.geotrellis.constants import SPATIAL
from geopyspark.tests.python_test_utils import geotiff_test_path
from geopyspark.geotrellis.geotiff import get
from geopyspark.tests.base_test_class import BaseTestClass


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
                    rasterio_tiles.append({'cells': src.read(),
                                           'no_data_value': src.nodata})
                else:
                    for window in windows:
                        rasterio_tiles.append(
                            {'cells': src.read(window=window),
                             'no_data_value': src.nodata})

        return rasterio_tiles


class Multiband(S3GeoTiffIOTest, BaseTestClass):
    mock_wrapper = BaseTestClass.pysc._gateway.jvm.geopyspark.geotrellis.testkit.MockS3ClientWrapper
    client = mock_wrapper.mockClient()

    key = "one-month-tiles-multiband/result.tif"
    bucket = "test"

    uri = "s3://test/one-month-tiles-multiband/result.tif"
    file_path = geotiff_test_path(key)
    options = {"s3Client": "mock"}

    in_file = open(file_path, "rb")
    cells = in_file.read()
    in_file.close()

    @pytest.fixture(scope='class', autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def read_multiband_geotrellis(self, opt=options):
        self.client.putObject(self.bucket, self.key, self.cells)
        result = get(BaseTestClass.pysc,
                     SPATIAL,
                     self.uri,
                     s3_client=opt['s3Client'],
                     max_tile_size=opt.get('maxTileSize'))

        return [tile[1] for tile in result.to_numpy_rdd().collect()]

    def test_whole_tiles(self):
        geotrellis_tiles = self.read_multiband_geotrellis()
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], False)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x.cells == y['cells']).all())

    def windowed_result_checker(self, windowed_tiles):
        self.assertEqual(len(windowed_tiles), 4)

    def test_windowed_tiles(self):
        geotrellis_tiles = self.read_multiband_geotrellis({"s3Client": "mock", "maxTileSize": 256})
        rasterio_tiles = self.read_geotiff_rasterio([self.file_path], True)

        self.windowed_result_checker(geotrellis_tiles)

        for x, y in zip(geotrellis_tiles, rasterio_tiles):
            self.assertTrue((x.cells == y['cells']).all())


if __name__ == "__main__":
    unittest.main()
