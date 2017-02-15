from pyspark import RDD, SparkContext
from pyspark.serializers import AutoBatchedSerializer
from geopyspark.avroserializer import AvroSerializer

def decode_java_rdd(pysc, java_rdd, schema, avroregistry):
    if avroregistry is None:
        ser = AvroSerializer(schema)
    else:
        ser = AvroSerializer(schema, avroregistry)

    return (RDD(java_rdd, pysc, AutoBatchedSerializer(ser)), schema)
