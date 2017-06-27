from geopyspark.geopyspark_utils import ensure_pyspark
ensure_pyspark()

import os
import glob
from pkg_resources import resource_filename

from geopyspark.geopyspark_constants import JAR

from pyspark import RDD, SparkConf, SparkContext
from pyspark.serializers import AutoBatchedSerializer


def map_key_input(key_type, is_boundable):
    """Gets the mapped GeoTrellis type from the `key_type`.
    Args:
        key_type (str): The type of the ``K`` in the tuple, ``(K, V)`` in the RDD.
        is_boundable (bool): Is ``K`` boundable.
    Returns:
        The corresponding GeoTrellis type.
    """

    if is_boundable:
        if key_type == "spatial":
            return "SpatialKey"
        elif key_type == "spacetime":
            return "SpaceTimeKey"
        else:
            raise Exception("Could not find key type that matches", key_type)
    else:
        if key_type == "spatial":
            return "ProjectedExtent"
        elif key_type == "spacetime":
            return "TemporalProjectedExtent"
        else:
            raise Exception("Could not find key type that matches", key_type)

def create_python_rdd(pysc, jrdd, serializer):
    """Creates a Python RDD from a RDD from Scala.
    Args:
        jrdd (org.apache.spark.api.java.JavaRDD): The RDD that came from Scala.
        serializer (:class:`~geopyspark.AvroSerializer` or pyspark.serializers.AutoBatchedSerializer(AvroSerializer)):
            An instance of ``AvroSerializer`` that is either alone, or wrapped by ``AutoBatchedSerializer``.
    Returns:
        ``pyspark.RDD``
    """

    if isinstance(serializer, AutoBatchedSerializer):
        return RDD(jrdd, pysc, serializer)
    else:
        return RDD(jrdd, pysc, AutoBatchedSerializer(serializer))

def geopyspark_conf(master=None, appName=None, additional_jar_dirs=[]):
    """Construct the base SparkConf for use with GeoPySpark.  This configuration
    object may be used as is , or may be adjusted according to the user's needs.

    Args:
        appName (string): The name of the application, as seen in the Spark
            console
        master (string): The master URL to connect to, such as "local" to run
            locally with one thread, "local[4]" to run locally with 4 cores, or
            "spark://master:7077" to run on a Spark standalone cluster.
        additional_jar_dirs (optional, list): A list of directory locations that
            might contain JAR files needed by the current script.  Already
            includes $(cwd)/jars and /opt/jars.

    Returns:
        [SparkConf]
    """
    conf = SparkConf()

    if not appName:
        raise ValueError("An appName must be provided")
    else:
        conf.setAppName(appName)

    if not master:
        conf.setMaster("local[*]")
    else:
        conf.setMaster(master)

    conf.set(key='spark.ui.enabled', value='false')
    conf.set(key='spark.serializer', value='org.apache.spark.serializer.KryoSerializer')
    conf.set(key='spark.kryo.registrator', value='geotrellis.spark.io.kryo.KryoRegistrator')

    current_location = os.path.dirname(os.path.realpath(__file__))
    cwd = os.getcwd()

    local_prefixes = [
        os.path.abspath(os.path.join(current_location, 'jars')),
        os.path.abspath(os.path.join(cwd, 'jars')),
        os.path.abspath(os.path.join(cwd, '../geopyspark/jars')),
        '/opt/jars'
    ]
    possible_jars = [os.path.join(prefix, '*.jar') for prefix in local_prefixes]
    configuration = os.path.join(current_location, 'command', 'geopyspark.conf')

    if os.path.isfile(configuration):
        with open(os.path.join(configuration)) as conf:
            possible_jars.append(os.path.relpath(conf.read(), cwd))

    jar = os.path.abspath(resource_filename('geopyspark.jars', JAR))
    jar_dir = os.path.dirname(jar)
    if jar_dir not in local_prefixes:
        possible_jars.append(jar)

    returned = [glob.glob(jar_files) for jar_files in possible_jars]
    jars = [jar for sublist in returned for jar in sublist]

    if len(jars) == 0:
        raise IOError("Failed to find any jars. Looked at these paths {}".format(possible_jars))

    jar_string = ",".join(jars)
    conf.set(key='spark.jars', value=jar_string)

    if 'TRAVIS' in os.environ:
        conf.set(key='spark.driver.memory', value='2G')
        conf.set(key='spark.executor.memory', value='2G')
    else:
        conf.set(key='spark.driver.memory', value='8G')
        conf.set(key='spark.executor.memory', value='8G')

    return conf
