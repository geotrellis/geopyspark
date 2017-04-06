""""This module contains functions that create RDDs from files.

There is only one function found within this module at this time, geotiff_rdd.
"""

from geopyspark.constants import TILE
from geopyspark.rdd import RasterRDD

def geotiff_rdd(geopysc,
                rdd_type,
                uri,
                options=None,
                **kwargs):

    """Creates a RDD from GeoTiffs that are located on the local file system, HDFS, or S3.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same saptial type.
        uri (str): The path to a given file/directory.
        options (dict, optional): A dictionary of different options that are used
            when creating the RDD. This defaults to None. If None, then the
            RDD will be created using the default options for the given backend
            in GeoTrellis. Note: key values should be in camel case, as this is
            the style that is used in Scala.

            These are the options when using the local file system or HDFS:
                crs (str, optional): The CRS that the output tiles should be
                    in. The CRS must be in the well-known name format. If None,
                    then the CRS that the tiles were originally in will be used.
                timeTag (str, optional): The name of the tiff tag that contains
                    the time stamp for the tile. If None, then the default value
                    is: 'TIFFTAG_DATETIME'.
                timeFormat (str, optional): The pattern of the time stamp for
                    java.time.format.DateTimeFormatter to parse. If None,
                    then the default value is: 'yyyy:MM:dd HH:mm:ss".
                maxTileSize (int, optional): The max size of each tile in the
                    resulting RDD. If the size is smaller than a read in tile,
                    then that tile will be broken into tiles of the specified
                    size. If None, then the whole tile will be read in.
                numPartitions (int, optional): The number of repartitions Spark
                    will make when the data is repartitioned. If None, then the
                    data will not be repartitioned.
                chunkSize (int, optional): How many bytes of the file should be
                    read in at a time. If None, then files will be read in 65536
                    byte chunks.

            S3 has the above options in addition to this:
                s3Client (st, optional): Which S3Cleint to use when reading
                    GeoTiffs. There are currently two options: 'default' and
                    'mock'. If None, 'defualt' is used. Note: 'mock' should
                    only be used in unit tests.

        **kwargs: Option parameters can also be entered as keyword arguements.
            Note: Defining both options and keyword arguements will cause the
            keyword arguements to be ignored in favor of options.

    Returns:
        RDD: A RDD that contains tuples of dictionaries, (K, V).
            K (dict): The projected extent information of the GeoTiff.
                Which is the pyhiscal extent and the CRS of the GeoTiff.
            V (dict): The raster tile information of the GeoTiff.
                Which is the Tile data itself represented as a numpy array,
                and the no_data_value of the Tile, if any.

    Examples:
        Reading a local GeoTiff that does not have a time component with the
        default options.

        >>> geotiff_rdd(geopysc, SPATIAL, 'file://path/to/my/geotiff.tif')
        RDD

        Reading a GeoTiff from S3 that does have a time component. An option
        parameter is also passed in which specifies that each GeoTiff should
        be cut up into 256x256 tiles.

        >>> geotiff_rdd(geopysc, SPACETIME, 's3://bucket/data/september_images/', maxTileSize=256)
        RDD
    """

    key = geopysc.map_key_input(rdd_type, False)

    if kwargs and not options:
        options = kwargs

    if uri.startswith("s3://"):
        key_and_bucket_uri = uri.split("s3://")[1]
        (bucket, prefix) = key_and_bucket_uri.split("/", 1)

        if not options:
            srdd = geopysc._s3_geotiff_rdd.getRDD(key,
                                                  bucket,
                                                  prefix,
                                                  geopysc.sc)
        else:
            srdd = geopysc._s3_geotiff_rdd.getRDD(key,
                                                  bucket,
                                                  prefix,
                                                  options,
                                                  geopysc.sc)

    else:
        if not options:
            srdd = geopysc._hadoop_geotiff_rdd.getRDD(key,
                                                      uri,
                                                      geopysc.sc)
        else:
            srdd = geopysc._hadoop_geotiff_rdd.getRDD(key,
                                                      uri,
                                                      options,
                                                      geopysc.sc)

    return RasterRDD(geopysc, rdd_type, srdd)
