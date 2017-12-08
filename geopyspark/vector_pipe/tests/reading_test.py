import unittest
import pytest

from geopyspark.vector_pipe import osm_reader
from geopyspark.vector_pipe.vector_pipe_constants import LoggingStrategy
from geopyspark.tests.base_test_class import BaseTestClass


# TODO: Make this run as a unit test
class ReadingTest(BaseTestClass):

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_reading_snapshot_nothing(self):
        read = osm_reader.read("/tmp/andorra.orc", logging_strategy='Nothing')
        points = read.get_point_features_rdd()
        lines = read.get_line_features_rdd()
        polys = read.get_polygon_features_rdd()
        mpolys = read.get_multipolygon_features_rdd()

    def test_reading_snapshot_log4(self):
        read = osm_reader.read("/tmp/andorra.orc", logging_strategy=LoggingStrategy.LOG4J)
        points = read.get_point_features_rdd()
        lines = read.get_line_features_rdd()
        polys = read.get_polygon_features_rdd()
        mpolys = read.get_multipolygon_features_rdd()

    def test_reading_snapshot_std(self):
        read = osm_reader.read("/tmp/andorra.orc", logging_strategy=LoggingStrategy.STD)
        points = read.get_point_features_rdd()
        lines = read.get_line_features_rdd()
        polys = read.get_polygon_features_rdd()
        mpolys = read.get_multipolygon_features_rdd()

    def test_reading_historical(self):
        read = osm_reader.read("/tmp/andorra.orc", logging_strategy='Nothing')
        points = read.get_point_features_rdd()
        lines = read.get_line_features_rdd()
        polys = read.get_polygon_features_rdd()
        mpolys = read.get_multipolygon_features_rdd()

    def test_rasterization(self):
        read = osm_reader.read("/tmp/andorra.orc", view='Historical', logging_strategy='Nothing')
        points = read.get_point_features_rdd()
        lines = read.get_line_features_rdd()
        polys = read.get_polygon_features_rdd()
        mpolys = read.get_multipolygon_features_rdd()

if __name__ == "__main__":
    unittest.main()
