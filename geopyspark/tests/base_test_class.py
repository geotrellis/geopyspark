from pyspark import SparkContext
from geopyspark.geopycontext import GeoPyContext
from geopyspark.avroregistry import AvroRegistry

import unittest


class BaseTestClass(unittest.TestCase):
    pysc = SparkContext(master="local[*]", appName="test")
    geopysc = GeoPyContext(pysc)
