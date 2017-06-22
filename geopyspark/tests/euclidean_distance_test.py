import os
import unittest
import numpy as np

import pytest

from shapely.geometry import Point, MultiPoint, LineString
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.geotrellis.rdd import TiledRasterRDD
from geopyspark.geotrellis.constants import SPATIAL

import pyproj

class EuclideanDistanceTest(BaseTestClass):
    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    latlong = pyproj.Proj(init='epsg:4326')
    webmerc = pyproj.Proj(init='epsg:3857')
    pts_wm = MultiPoint([pyproj.transform(latlong, webmerc, 1, 1),
                         pyproj.transform(latlong, webmerc, 2, 2)])
    pts = MultiPoint([(1,1), (2,2)])

    def test_euclideandistance(self):
        def mapTransform(layoutDefinition, spatialKey):
            ex = layoutDefinition.extent
            x_range = ex.xmax - ex.xmin
            xinc = x_range/layoutDefinition.tileLayout.layoutCols
            yrange = ex.ymax - ex.ymin
            yinc = yrange/layoutDefinition.tileLayout.layoutRows

            return {'xmin': ex.xmin + xinc * spatialKey['col'],
                    'xmax': ex.xmin + xinc * (spatialKey['col'] + 1),
                    'ymin': ex.ymax - yinc * (spatialKey['row'] + 1),
                    'ymax': ex.ymax - yinc * spatialKey['row']}

        def gridToMap(layoutDefinition, spatialKey, px, py):
            ex = mapTransform(layoutDefinition, spatialKey)
            x_range = ex['xmax'] - ex['xmin']
            xinc = x_range/layoutDefinition.tileLayout.tileCols
            yrange = ex['ymax'] - ex['ymin']
            yinc = yrange/layoutDefinition.tileLayout.tileRows
            return (ex['xmin'] + xinc * (px + 0.5), ex['ymax'] - yinc * (py + 0.5))

        def distanceToGeom(layoutDefinition, spatialKey, geom, px, py):
            x, y = gridToMap(layoutDefinition, spatialKey, px, py)
            return geom.distance(Point(x, y))

        tiled = TiledRasterRDD.euclidean_distance(BaseTestClass.pysc, self.pts_wm, 3857, 7)
        result = tiled.stitch()['data'][0]

        arr = np.zeros((256,256), dtype=float)
        it = np.nditer(arr, flags=['multi_index'])
        while not it.finished:
            py, px = it.multi_index
            arr[py][px] = distanceToGeom(tiled.layer_metadata.layout_definition,
                                         {'col': 64, 'row':63},
                                         self.pts_wm,
                                         px,
                                         py)
            it.iternext()

        self.assertTrue(np.all(abs(result - arr) < 1e-8))


if __name__ == "__main__":
    unittest.main()
