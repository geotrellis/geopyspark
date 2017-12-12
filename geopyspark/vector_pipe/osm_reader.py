from geopyspark.geopyspark_utils import ensure_pyspark
ensure_pyspark()
from geopyspark import get_spark_context, create_python_rdd
from geopyspark.vector_pipe import Feature, Properties
from geopyspark.vector_pipe.features_collection import FeaturesCollection

from pyspark.sql import SparkSession


__all__ = ['from_orc', 'from_dataframe']


def from_orc(source):
    """Reads in OSM data from an orc file that is located either locally or on S3. The
    resulting data will be read in as an instance of :class:`~geopyspark.vector_pipe.features_collection.FeaturesCollection`.

    Args:
        source (str): The path or URI to the orc file to be read. Can either be a local file, or
            a file on S3.

            Note:
                Reading a file from S3 requires additional setup depending on the environment
                and how the file is being read.

                The following describes the parameters that need to be set depending on
                how the files are to be read in. However, **if reading a file on EMR, then
                the access key and secret key do not need to be set**.

                If using ``s3a://``, then the following ``SparkConf`` parameters need to be set:
                    - ``spark.hadoop.fs.s3a.impl``
                    - ``spark.hadoop.fs.s3a.access.key``
                    - ``spark.hadoop.fs.s3a.secret.key``

                If using ``s3n://``, then the following ``SparkConf`` parameters need to be set:
                    - ``spark.hadoop.fs.s3n.access.key``
                    - ``spark.hadoop.fs.s3n.secret.key``

                An alternative to passing in your S3 credentials to ``SparkConf`` would be
                to export them as environment variables:
                    - ``AWS_ACCESS_KEY_ID=YOUR_KEY``
                    - ``AWS_SECRET_ACCESS_KEY_ID=YOUR_SECRET_KEY``

    Returns:
        :class:`~geopyspark.vector_pipe.features_collection.FeaturesCollection`
    """

    pysc = get_spark_context()
    session = SparkSession.builder.config(conf=pysc.getConf()).enableHiveSupport().getOrCreate()
    features = pysc._jvm.geopyspark.vectorpipe.io.OSMReader.fromORC(session._jsparkSession, source)

    return FeaturesCollection(features)

def from_dataframe(dataframe):
    """Reads OSM data from a Spark ``DataFrame``. The resulting data will be read
    in as an instance of :class:`~geopyspark.vector_pipe.features_collection.FeaturesCollection`.

    Args:
        dataframe (DataFrame): A Spark ``DataFrame`` that contains the OSM data.

    Returns:
        :class:`~geopyspark.vector_pipe.features_collection.FeaturesCollection`
    """

    pysc = get_spark_context()
    features = pysc._jvm.geopyspark.vectorpipe.io.OSMReader.fromDataFrame(dataframe._jdf)

    return FeaturesCollection(features)
