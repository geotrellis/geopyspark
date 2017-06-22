from geopyspark.geopyspark_utils import check_environment
import geopyspark.geotrellis.converters

check_environment()
from pyspark import RDD
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

