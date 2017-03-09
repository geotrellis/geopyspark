from pyspark import SparkContext
from geopyspark.geopycontext import GeoPyContext

import unittest
import pytest


class BaseTestClass(unittest.TestCase):
    pysc = SparkContext(master="local[*]", appName="test")
    geopysc = GeoPyContext(pysc)
