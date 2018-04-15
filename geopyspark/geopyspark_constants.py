"""GeoPySpark package constants."""
from os import path

"""GeoPySpark version."""
VERSION = '0.3.0.gm.4'

"""Backend jar name."""
JAR = 'geopyspark-assembly-' + VERSION + '.jar'

"""The current location of this file."""
CWD = path.abspath(path.dirname(__file__))
