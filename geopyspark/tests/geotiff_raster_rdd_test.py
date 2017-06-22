import unittest
from os import walk, path
import rasterio
import pytest
import numpy as np

from geopyspark.geotrellis import SPATIAL, RasterRDD
from geopyspark.geotrellis.constants import INT32, BOOLRAW
from geopyspark.tests.python_test_utils import geotiff_test_path
from geopyspark.geotrellis.geotiff_rdd import get
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
    result = get(BaseTestClass.geopysc, SPATIAL, dir_path)

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.geopysc.pysc._gateway.close()

    def test_to_numpy_rdd(self, option=None):
        pyrdd = self.result.to_numpy_rdd()
        (key, tile) = pyrdd.first()
        self.assertEqual(tile['data'].shape, (2, 512, 512))

    def test_collect_metadata(self, options=None):
        md = self.result.collect_metadata()
        self.assertTrue('+proj=longlat' in md.crs)
        self.assertTrue('+datum=WGS84' in md.crs)

    def test_collect_metadata_crs_override(self, options=None):
        md = self.result.collect_metadata(crs='EPSG:3857')
        self.assertTrue('+proj=merc' in md.crs)

    def test_cut_tiles(self, options=None):
        md = self.result.collect_metadata(tile_size=100)
        tiles = self.result.cut_tiles(md)
        records_before = self.result.srdd.rdd().count()
        records_after = tiles.srdd.rdd().count()
        self.assertTrue(records_after > records_before)

    def test_reproject(self, options=None):
        tiles = self.result.reproject("EPSG:3857")
        md = tiles.collect_metadata()
        self.assertTrue('+proj=merc' in md.crs)

    def test_to_tiled_raster(self):
        md = self.result.collect_metadata()
        tiled = self.result.tile_to_layout(md)
        converted = self.result.to_tiled_layer()

        self.assertDictEqual(tiled.layer_metadata.to_dict(),
                             converted.layer_metadata.to_dict())
    '''

    def test_to_int(self):
        arr = np.array([[0.4324323432124, 0.0, 0.0],
                        [1.0, 1.0, 1.0]], dtype=float)

        epsg_code = 3857
        extent = {'xmin': 0.0, 'ymin': 0.0, 'xmax': 10.0, 'ymax': 10.0}
        projected_extent = {'extent': extent, 'epsg': epsg_code}

        tile = {'data': arr, 'no_data_value': float('nan')}
        rdd = BaseTestClass.geopysc.pysc.parallelize([(self.projected_extent, tile)])
        raster_rdd = RasterRDD.from_numpy_rdd(BaseTestClass.geopysc, SPATIAL, rdd)

        converted = raster_rdd.convert_data_type(INT32)
        arr = converted.to_numpy_rdd().first()[1]['data']

        self.assertEqual(arr.dtype, np.int64)

    def test_to_boolraw(self):
        converted = self.result.convert_data_type(BOOLRAW)
        arr = converted.to_numpy_rdd().first()[1]['data']

        self.assertEqual(arr.dtype, np.uint8)
    '''


if __name__ == "__main__":
    unittest.main()
