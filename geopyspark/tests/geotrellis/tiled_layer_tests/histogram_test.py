import unittest
import pytest
import numpy as np

from geopyspark.geotrellis import SpatialKey, Tile, Histogram
from geopyspark.geotrellis.constants import LayerType
from geopyspark.geotrellis.layer import TiledRasterLayer
from geopyspark.tests.base_test_class import BaseTestClass


class HistogramTest(BaseTestClass):
    extent = {'xmin': 0.0, 'ymin': 0.0, 'xmax': 33.0, 'ymax': 33.0}
    layout = {'layoutCols': 1, 'layoutRows': 1, 'tileCols': 4, 'tileRows': 4}
    metadata = {'cellType': 'float32ud-1.0',
                'extent': extent,
                'crs': '+proj=longlat +datum=WGS84 +no_defs ',
                'bounds': {
                    'minKey': {'col': 0, 'row': 0},
                    'maxKey': {'col': 0, 'row': 0}},
                'layoutDefinition': {
                    'extent': extent,
                    'tileLayout': {'tileCols': 4, 'tileRows': 4, 'layoutCols': 1, 'layoutRows': 1}}}

    spatial_key = SpatialKey(0, 0)

    arr = np.array([[[1.0, 1.0, 1.0, 1.0],
                     [2.0, 2.0, 2.0, 2.0],
                     [3.0, 3.0, 3.0, 3.0],
                     [4.0, 4.0, 4.0, 4.0]]], dtype=float)

    tile = Tile(arr, 'FLOAT', -500)
    rdd = BaseTestClass.pysc.parallelize([(spatial_key, tile)])
    tiled = TiledRasterLayer.from_numpy_rdd(LayerType.SPATIAL, rdd, metadata)
    hist = tiled.get_histogram()

    def test_dict(self):
        dict_hist = self.hist.to_dict()
        encoded_hist = Histogram.from_dict(dict_hist)

        self.assertEqual(encoded_hist.min_max(), self.hist.min_max())
        self.assertEqual(encoded_hist.mean(), self.hist.mean())
        self.assertEqual(encoded_hist.bucket_count(), self.hist.bucket_count())

    def test_min(self):
        self.assertEqual(self.hist.min(), 1.0)

    def test_max(self):
        self.assertEqual(self.hist.max(), 4.0)

    def test_min_max(self):
        self.assertEqual(self.hist.min_max(), (1.0, 4.0))

    def test_mean(self):
        self.assertEqual(self.hist.mean(), 2.5)

    def test_mode(self):
        arr2 = np.array([[[1.0, 1.0, 1.0, 1.0],
                          [2.0, 2.0, 2.0, 2.0],
                          [1.0, 3.0, 3.0, 3.0],
                          [4.0, 4.0, 4.0, 4.0]]], dtype=float)

        tile2 = Tile(arr2, 'FLOAT', -500)
        rdd2 = BaseTestClass.pysc.parallelize([(self.spatial_key, tile2)])
        tiled2 = TiledRasterLayer.from_numpy_rdd(LayerType.SPATIAL, rdd2, self.metadata)
        hist2 = tiled2.get_histogram()

        self.assertEqual(hist2.mode(), 1.0)

    def test_quantile_breaks(self):
        result = self.hist.quantile_breaks(4)
        self.assertEqual(result, [1, 2, 3, 4])

    def test_median(self):
        self.assertEqual(self.hist.median(), 2.5)

    def test_cdf(self):
        expected_cdf = [(1.0, 0.25), (2.0, 0.5), (3.0, 0.75), (4.0, 1.0)]

        self.assertEqual(self.hist.cdf(), expected_cdf)

    def test_bucket_count(self):
        self.assertEqual(self.hist.bucket_count(), 4)

    def test_values(self):
        self.assertEqual(self.hist.values(), [1.0, 2.0, 3.0, 4.0])

    def test_item_count(self):
        self.assertEqual(self.hist.item_count(3.0), 5)

    def test_bin_counts(self):
        metadata2 = {'cellType': 'int32ud-500',
                     'extent': self.extent,
                     'crs': '+proj=longlat +datum=WGS84 +no_defs ',
                     'bounds': {
                         'minKey': {'col': 0, 'row': 0},
                         'maxKey': {'col': 0, 'row': 0}},
                     'layoutDefinition': {
                         'extent': self.extent,
                         'tileLayout': {'tileCols': 4, 'tileRows': 4, 'layoutCols': 1, 'layoutRows': 1}}}

        arr2 = np.int8([[[1, 1, 1, 1],
                         [3, 1, 1, 1],
                         [4, 3, 1, 1],
                         [5, 4, 3, 1]]])

        tile2 = Tile(arr2, 'INT', -500)
        rdd2 = BaseTestClass.pysc.parallelize([(self.spatial_key, tile2)])
        tiled2 = TiledRasterLayer.from_numpy_rdd(LayerType.SPATIAL, rdd2,
                                                 metadata2)

        hist2 = tiled2.get_class_histogram()
        bin_counts = hist2.bin_counts()

        self.assertEqual(bin_counts, [(1, 10), (3, 3), (4, 2), (5, 1)])

    def test_merge(self):
        arr2 = np.array([[[1.0, 1.0, 1.0, 1.0],
                          [1.0, 1.0, 1.0, 1.0],
                          [1.0, 1.0, 1.0, 1.0],
                          [1.0, 1.0, 1.0, 1.0]]], dtype=float)

        tile2 = Tile(arr2, 'FLOAT', -500)
        rdd2 = BaseTestClass.pysc.parallelize([(self.spatial_key, tile2)])
        tiled2 = TiledRasterLayer.from_numpy_rdd(LayerType.SPATIAL, rdd2,
                                                 self.metadata)

        hist2 = tiled2.get_histogram()

        merged = self.hist.merge(hist2)


        self.assertEqual(merged.values(), [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(merged.mean(), 1.75)

    def test_dict_methods(self):
        dict_hist = self.hist.to_dict()
        # value produced by histogram of doubles
        self.assertEqual(dict_hist['maxBucketCount'], 80)

        rebuilt_hist = Histogram.from_dict(dict_hist)
        self.assertEqual(self.hist.min_max(), rebuilt_hist.min_max())


if __name__ == "__main__":
    unittest.main()
