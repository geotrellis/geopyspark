import unittest

from geopyspark.geopycontext import GeoPyContext


class BaseTestClass(unittest.TestCase):
    geopysc = GeoPyContext(master="local[*]", appName="test")
