import unittest
import pytest

from geopyspark.vector_pipe import osm_reader, Feature, CellValue
from geopyspark.vector_pipe.vector_pipe_constants import LoggingStrategy
from geopyspark.tests.base_test_class import BaseTestClass

from geopyspark.geotrellis.rasterize import rasterize_features


# TODO: Have this run as an actual unit test
class RasterizationTest(BaseTestClass):

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_rasterization(self):
        read = osm_reader.read("/tmp/andorra.orc",
                               view='Historical',
                               logging_strategy='Nothing')

        lines = read.get_line_features_rdd()
        polys = read.get_polygon_features_rdd()

        mapped_lines = lines.map(lambda feature: Feature(feature.geometry, CellValue(1, 0)))

        def assign_cellvalues(feature):
            tags = feature.properties.tags

            if 'playground' in tags:
                return Feature(feature.geometry, CellValue(3, 1))
            elif 'castle' in tags:
                return Feature(feature.geometry, CellValue(4, 1))
            else:
                return Feature(feature.geometry, CellValue(2, 1))

        mapped_polys = polys.map(lambda feature: assign_cellvalues(feature))

        unioned = BaseTestClass.pysc.union((mapped_lines, mapped_polys))
        result = rasterize_features(unioned, 4326, 1)


if __name__ == "__main__":
    unittest.main()
