import unittest
import pytest

from geopyspark.vector_pipe import osm_reader
from geopyspark.tests.base_test_class import BaseTestClass
from geopyspark.tests.python_test_utils import file_path


class ReadingOrcTest(BaseTestClass):
    features = osm_reader.from_orc(file_path("zerns.orc"))

    @pytest.fixture(autouse=True)
    def tearDown(self):
        yield
        BaseTestClass.pysc._gateway.close()

    def test_reading_rdds_from_orc(self):

        self.assertTrue(self.features.get_multipolygon_features_rdd().isEmpty())

        self.assertTrue(self.features.get_point_features_rdd().count(), 1)
        self.assertEqual(self.features.get_line_features_rdd().count(), 8)
        self.assertEqual(self.features.get_polygon_features_rdd().count(), 5)

    def test_reading_tags_from_orc(self):
        ex_point_tags = ['traffic_signals', 'backward']
        ex_line_tags = ['Big Rd', 'PA 73', 'Layfield Rd', 'Jackson', '19525']
        ex_polygon_tags = ["en:Zern's Farmer's Market",
                           'E Philadelphia Avenue',
                           'LakePond',
                           'Gilbertsville']

        self.assertEqual(self.features.get_multipolygon_tags(), {})

        point_tags = self.features.get_point_tags().values()
        line_tags = self.features.get_line_tags().values()
        polygon_tags = self.features.get_polygon_tags().values()

        for tag in ex_point_tags:
            self.assertTrue(tag in point_tags)

        for tag in ex_line_tags:
            self.assertTrue(tag in line_tags)

        for tag in ex_polygon_tags:
            self.assertTrue(tag in polygon_tags)


if __name__ == "__main__":
    unittest.main()
