"""This module contains functions that create ``RasterRDD`` from files."""

from geopyspark import map_key_input
from geopyspark.geotrellis.rdd import RasterRDD
from functools import reduce

def get(pysc,
        rdd_type,
        uri,
        options=None,
        **kwargs):

    """Creates a ``RasterRDD`` from GeoTiffs that are located on the local file system, ``HDFS``,
    or ``S3``.

    Args:
        pysc (pyspark.context.SparkContext): The ``SparkContext`` being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: ``SPATIAL`` and ``SPACETIME``.

            Note:
                All of the GeoTiffs must have the same saptial type.
        uri (str): The path to a given file/directory.
        options (dict, optional): A dictionary of different options that are used
            when creating the RDD. This defaults to ``None``. If ``None``, then the
            RDD will be created using the default options for the given backend
            in GeoTrellis.

            Note:
                Key values in the ``dict`` should be in camel case, as this is the style that is
                used in Scala.

            These are the options when using the local file system or ``HDFS``:
                * **crs** (str, optional): The CRS that the output tiles should be
                    in. The CRS must be in the well-known name format. If ``None``,
                    then the CRS that the tiles were originally in will be used.
                * **timeTag** (str, optional): The name of the tiff tag that contains
                    the time stamp for the tile. If ``None``, then the default value
                    is: ``TIFFTAG_DATETIME``.
                * **timeFormat** (str, optional): The pattern of the time stamp for
                    java.time.format.DateTimeFormatter to parse. If ``None``,
                    then the default value is: ``yyyy:MM:dd HH:mm:ss``.
                * **maxTileSize** (int, optional): The max size of each tile in the
                    resulting RDD. If the size is smaller than a read in tile,
                    then that tile will be broken into tiles of the specified
                    size. If ``None``, then the whole tile will be read in.
                * **numPartitions** (int, optional): The number of repartitions Spark
                    will make when the data is repartitioned. If ``None``, then the
                    data will not be repartitioned.
                * **chunkSize** (int, optional): How many bytes of the file should be
                    read in at a time. If None, then files will be read in 65536
                    byte chunks.

            ``S3`` has the above options in addition to this:
                * **s3Client** (str, optional): Which ``S3Cleint`` to use when reading
                    GeoTiffs. There are currently two options: ``default`` and
                    ``mock``. If ``None``, ``defualt`` is used.

                    Note:
                        ``mock`` should only be used in unit tests and debugging.

        **kwargs: Option parameters can also be entered as keyword arguements.

    Note:
        Defining both ``options`` and ``kwargs`` will cause the ``kwargs`` to be ignored in favor
        of ``options``.

    Returns:
        :class:`~geopyspark.geotrellis.rdd.RasterRDD`
    """

    geotiff_rdd = pysc._gateway.jvm.geopyspark.geotrellis.io.geotiff.GeoTiffRDD

    key = map_key_input(rdd_type, False)

    if kwargs and not options:
        options = kwargs

    if options:
        if isinstance(uri, list):
            srdd = geotiff_rdd.get(pysc._jsc.sc(),
                                   key,
                                   uri,
                                   options)
        else:
            srdd = geotiff_rdd.get(pysc._jsc.sc(),
                                   key,
                                   [uri],
                                   options)
    else:
        if isinstance(uri, list):
            srdd = geotiff_rdd.get(pysc._jsc.sc(),
                                   key,
                                   uri,
                                   {})
        else:
            srdd = geotiff_rdd.get(pysc._jsc.sc(),
                                   key,
                                   [uri],
                                   {})

    return RasterRDD(pysc, rdd_type, srdd)
