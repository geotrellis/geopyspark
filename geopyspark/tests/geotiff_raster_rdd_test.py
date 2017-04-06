import unittest
from os import walk, path
import rasterio

from geopyspark.constants import SPATIAL
from geopyspark.tests.python_test_utils import check_directory, geotiff_test_path
from geopyspark.geotrellis.geotiff_rdd import geotiff_rdd
from geopyspark.tests.base_test_class import BaseTestClass


check_directory()


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
                    rasterio_tiles.append({'data': src.read(),
                                           'no_data_value': src.nodata})
                else:
                    for window in windows:
                        rasterio_tiles.append(
                            {'data': src.read(window=window),
                             'no_data_value': src.nodata})

        return rasterio_tiles

class Multiband(GeoTiffIOTest, BaseTestClass):
    dir_path = geotiff_test_path("one-month-tiles-multiband/")
    gps = BaseTestClass.geopysc
    result = geotiff_rdd(gps, SPATIAL, dir_path)

    def test_to_numpy_rdd(self, option=None):
        pyrdd = self.result.to_numpy_rdd()
        recs = pyrdd.collect()
        (key,tile) = recs[0]
        self.assertTrue('extent' in key.keys())
        self.assertEqual(tile['data'].shape, (2, 512, 512))

    def test_collect_metadata(self, options=None):
        md = self.result.collect_metadata()
        self.assertTrue('+proj=longlat' in md['crs'])
        self.assertTrue('+datum=WGS84' in md['crs'])

    def test_collect_metadata_crs_override(self, options=None):
        md = self.result.collect_metadata('EPSG:3857')
        self.assertTrue('+proj=merc' in md['crs'])

    def test_cut_tiles(self, options=None):
        md = self.result.collect_metadata(tile_size=100)
        tiles = self.result.cut_tiles(md)
        records_before = self.result.srdd.rdd().count()
        records_after = tiles.srdd.rdd().count()
        self.assertTrue(records_after > records_before)

    def test_reproject(self, options=None):
        tiles = self.result.reproject("EPSG:3857")
        md = tiles.collect_metadata()
        self.assertTrue('+proj=merc' in md['crs'])


if __name__ == "__main__":
    unittest.main()
