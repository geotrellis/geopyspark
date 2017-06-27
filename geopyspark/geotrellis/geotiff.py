"""This module contains functions that create ``RasterLayer`` from files."""

from geopyspark import map_key_input
from geopyspark.geotrellis.layer import RasterLayer
from functools import reduce


def get(pysc,
        rdd_type,
        uri,
        crs=None,
        max_tile_size=None,
        num_partitions=None,
        chunk_size=None,
        time_tag=None,
        time_format=None,
        s3_client=None):

    """Creates a ``RasterLayer`` from GeoTiffs that are located on the local file system, ``HDFS``,
    or ``S3``.

    Args:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: ``SPATIAL`` and ``SPACETIME``.

            Note:
                All of the GeoTiffs must have the same saptial type.
        uri (str): The path to a given file/directory.
        crs (str, optional): The CRS that the output tiles should be
            in. The CRS must be in the well-known name format. If ``None``,
            then the CRS that the tiles were originally in will be used.
        max_tile_size (int, optional): The max size of each tile in the
            resulting Layer. If the size is smaller than a read in tile,
            then that tile will be broken into tiles of the specified
            size. If ``None``, then the whole tile will be read in.
        num_partitions (int, optional): The number of repartitions Spark
            will make when the data is repartitioned. If ``None``, then the
            data will not be repartitioned.
        chunk_size (int, optional): How many bytes of the file should be
            read in at a time. If ``None``, then files will be read in 65536
            byte chunks.
        time_tag (str, optional): The name of the tiff tag that contains
            the time stamp for the tile. If ``None``, then the default value
            is: ``TIFFTAG_DATETIME``.
        time_format (str, optional): The pattern of the time stamp for
            java.time.format.DateTimeFormatter to parse. If ``None``,
            then the default value is: ``yyyy:MM:dd HH:mm:ss``.
        s3_client (str, optional): Which ``S3Cleint`` to use when reading
            GeoTiffs from S3. There are currently two options: ``default`` and
            ``mock``. If ``None``, ``defualt`` is used.

            Note:
                ``mock`` should only be used in unit tests and debugging.

    Returns:
        :class:`~geopyspark.geotrellis.rdd.RasterLayer`
    """

    geotiff_rdd = pysc._gateway.jvm.geopyspark.geotrellis.io.geotiff.GeoTiffRDD

    key = map_key_input(rdd_type, False)

    options = {}

    if time_tag:
        options['timeTag'] = time_tag

    if time_format:
        options['timeFormat'] = time_format

    if crs:
        options['crs'] = crs

    if max_tile_size:
        options['maxTileSize'] = max_tile_size

    if chunk_size:
        options['chunkSize'] = chunk_size

    if s3_client:
        options['s3Client'] = s3_client

    if num_partitions:
        options['numPartitions'] = num_partitions

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

    return RasterLayer(pysc, rdd_type, srdd)
