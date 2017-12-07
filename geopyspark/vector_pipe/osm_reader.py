from geopyspark.geopyspark_utils import ensure_pyspark
ensure_pyspark()
from geopyspark import get_spark_context, create_python_rdd
from geopyspark.vector_pipe import Feature, Properties
from geopyspark.vector_pipe.features_collection import FeaturesCollection
from geopyspark.vector_pipe.vector_pipe_constants import LoggingStrategy, View

from pyspark.sql import SparkSession


def read(source, view=View.SNAPSHOT, logging_strategy=LoggingStrategy.NOTHING):
    pysc = get_spark_context()
    session = SparkSession.builder.config(conf=pysc.getConf()).enableHiveSupport().getOrCreate()

    features = pysc._jvm.geopyspark.vectorpipe.io.OSMReader.read(session._jsparkSession,
                                                                 source,
                                                                 View(view).value,
                                                                 LoggingStrategy(logging_strategy).value)

    return FeaturesCollection(features)
