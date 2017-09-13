"""Contains functions needed to setup the environment so that GeoPySpark can run."""
import glob
import sys

import os
from os import path


def ensure_pyspark():
    if not [p for p in sys.path if 'py4j' in p]:
        add_pyspark_path()

def add_pyspark_path():
    """Adds SPARK_HOME to environment variables.

    Raises:
        KeyError if SPARK_HOME could not be found.

    Raises:
        ValueError if py4j zip file could not be found.
    """

    try:
        pyspark_home = os.environ["SPARK_HOME"]
        sys.path.append(path.join(pyspark_home, 'python'))

    except:
        raise KeyError("Could not find SPARK_HOME")

    try:
        py4j_zip = glob.glob(path.join(pyspark_home, 'python', 'lib', 'py4j-*-src.zip'))
        sys.path.append(py4j_zip[0])
    except:
        raise ValueError("Could not find the py4j zip in", path.join(pyspark_home, 'python', 'lib'), os.getcwd())
