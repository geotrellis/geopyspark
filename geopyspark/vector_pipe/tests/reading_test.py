import unittest
import pytest

from geopyspark.vector_pipe import osm_reader
from geopyspark.tests.base_test_class import BaseTestClass


# TODO: Make this run as a unit test
class ReadingTest(BaseTestClass):

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_reading(self):
        read = osm_reader.read("/tmp/andorra.orc")
        points = read.get_point_features_rdd()
        lines = read.get_line_features_rdd()
        polys = read.get_polygon_features_rdd()
        mpolys = read.get_multipolygon_features_rdd()


if __name__ == "__main__":
    unittest.main()
