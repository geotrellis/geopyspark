"""Methods for reading, querying, and saving tile layers to and from GeoTrellis Catalogs.

Because GeoPySpark represents all raster data as 3D numpy arrays, data that is read/written out
will be in a multiband format; regardless of how the data was originally formatted.
"""

import json

from collections import namedtuple
from geopyspark.rdd import TiledRasterRDD
from geopyspark.constants import SPATIAL, TILE, ZORDER
from shapely.geometry import Polygon
from shapely.wkt import dumps
from urllib.parse import urlparse


_mapped_builds = {}
_mapped_serializers = {}
_builds = namedtuple('Builds', ('store', 'reader', 'value_reader', 'writer'))



def _construct_catalog(geopysc, new_uri, options):
    if new_uri not in _mapped_builds:

        parsed_uri = urlparse(new_uri)
        backend = parsed_uri.scheme

        if backend == 'hdfs':
            store = geopysc._store_factory.buildHadoop(new_uri)
            reader = geopysc._reader_factory.buildHadoop(store, geopysc.sc)
            value_reader = geopysc._value_reader_factory.buildHadoop(store)
            writer = geopysc._writer_factory.buildHadoop(store)

        elif backend == 'file':
            store = geopysc._store_factory.buildFile(new_uri[7:])
            reader = geopysc._reader_factory.buildFile(store, geopysc.sc)
            value_reader = geopysc._value_reader_factory.buildFile(store)
            writer = geopysc._writer_factory.buildFile(store)

        elif backend == 's3':
            store = geopysc._store_factory.buildS3(parsed_uri.netloc, parsed_uri.path[1:])
            reader = geopysc._reader_factory.buildS3(store, geopysc.sc)
            value_reader = geopysc._value_reader_factory.buildS3(store)
            writer = geopysc._writer_factory.buildS3(store)

        elif backend == 'cassandra':
            parameters = parsed_uri.query.split('&')
            parameter_dict = {}

            for param in parameters:
                split_param = param.split('=', 1)
                parameter_dict[split_param[0]] = split_param[1]

            store = geopysc._store_factory.buildCassandra(
                parameter_dict['host'],
                parameter_dict['username'],
                parameter_dict['password'],
                parameter_dict['keyspace'],
                parameter_dict['table'],
                options)

            reader = geopysc._reader_factory.buildCassandra(store, geopysc.sc)
            value_reader = geopysc._value_reader_factory.buildCassandra(store)
            writer = geopysc._writer_factory.buildCassandra(store,
                                                           parameter_dict['keyspace'],
                                                           parameter_dict['table'])

        elif backend == 'hbase':

            # The assumed uri looks like: hbase://zoo1, zoo2, ..., zooN: port/table
            (zookeepers, port) = parsed_uri.netloc.split(':')
            table = parsed_uri.path

            if 'master' in options:
                master = options['master']
            else:
                master = ""

            store = geopysc._store_factory.buildHBase(zookeepers, master, port, table)
            reader = geopysc._reader_factory.buildHBase(store, geopysc.sc)
            value_reader = geopysc._value_reader_factory.buildHBase(store)
            writer = geopysc._writer_factory.buildHBase(store, table)

        elif backend == 'accumulo':

            # The assumed uri looks like: accumulo://username:password/zoo1, zoo2/instance/table
            (user, password) = parsed_uri.netloc.split(':')
            split_parameters = parsed_uri.path.split('/')[1:]

            store = geopysc._store_factory.buildAccumulo(split_parameters[0],
                                                        split_parameters[1],
                                                        user,
                                                        password,
                                                        split_parameters[2])

            reader = geopysc._reader_factory.buildAccumulo(split_parameters[1],
                                                          store,
                                                          geopysc.sc)

            value_reader = geopysc._value_reader_factory.buildAccumulo(store)

            writer = geopysc._writer_factory.buildAccumulo(split_parameters[1],
                                                          store,
                                                          split_parameters[2])

        else:
            raise Exception("Cannot find Attribute Store for, {}".format(backend))

        _mapped_builds[new_uri] = _builds(store=store,
                                          reader=reader,
                                          value_reader=value_reader,
                                          writer=writer)

def read(geopysc,
         rdd_type,
         uri,
         layer_name,
         layer_zoom,
         options=None,
         **kwargs):

    """Reads a single, zoom layer from a GeoTrellis catalog.
    Note, this will read the entire layer. If only part of the layer is needed, consider using
    query instead.

    A layer can be read from various backends. These are the ones that are currently supported:
        Local Filesystem
        HDFS
        S3
        Cassandra
        HBase
        Accumulo

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same saptial type.
        uri (str): The Uniform Resource Identifier used to point towards the desired GeoTrellis
            catalog to be read from. The shape of this string varies depending on backend.

            Example uris for each backend:
                Local Filesystem: file://my_folder/my_catalog/
                HDFS: hdfs://my_folder/my_catalog/
                S3: s3://my_bucket/my_catalog/
                Cassandra: cassandra:name?username=user&password=pass&host=host1&keyspace=key&table=table
                HBase: hbase://zoo1, zoo2: port/table
                Accumulo: accumulo://username:password/zoo1, zoo2/instance/table
        layer_name (str): The name of the GeoTrellis catalog to be read from.
        layer_zoom (int): The zoom level of the layer that is to be read.
        options (dict, optional): Additional parameters for reading the layer for specific backends.
            The dictionary is only used for Cassandra and HBase, no other backend requires this
            to be set.

            Fields that can be set for Cassandra:
                replicationStrategy (str, optional): If not specified, then 'SimpleStrategy' will
                    be used.
                replicationFactor (int, optional): If not specified, then 1 will be used.
                localDc (str, optional): If not specified, then 'datacenter1' will be used.
                usedHostsPerRemoteDc (int, optional): If not specified, then 0 will be used.
                allowRemoteDCsForLocalConsistencyLevel (int, optional): If you'd like this feature,
                    then the value would be 1, Otherwise, the value should be 0. If not specified,
                    then 0 will be used.

            Fields that can be set for HBase:
                master (str, optional): If not specified, then 'null' will be used.
        **kwargs: The optional parameters can also be set as keywords arguments. The keywords must
            be in camel case. If both options and keywords are set, then the options will be used.

    Returns:
        RDD: A RDD that contains tuples of dictionaries, (key, tile).
            key (dict): The index of the tile within the layer. There are two different types
                of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys deal with data that have just
                a spatial component, whereas SpaceTimeKeys are for data with both a spatial and
                time component.

                Both SpatialKeys and SpaceTimeKeys share these fields:
                    col (int): The column number of the grid, runs east to west.
                    row (int): The row number of the grid, runs north to south.

                SpaceTimeKeys also have an additional field:
                    instant (int): The time stamp of the tile.
            tile (dict): The data of the tile.

                The fields to represent the tile:
                    data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                        Note, even if the data was originally singleband, it will be reformatted as
                        a multiband tile and read and saved as such.
                    no_data_value (optional): The no data value of the tile. Can be a range of
                        types including None.

    """

    if options:
        options = options
    elif kwargs:
        options = kwargs
    else:
        options = {}

    _construct_catalog(geopysc, uri, options)

    builds = _mapped_builds[uri]

    key = geopysc.map_key_input(rdd_type, True)
    srdd = builds.reader.read(key, layer_name, layer_zoom)

    return TiledRasterRDD(geopysc, key, srdd)

def read_value(geopysc,
               rdd_type,
               uri,
               layer_name,
               layer_zoom,
               col,
               row,
               zdt=None,
               options=None,
               **kwargs):

    """Reads a single tile from a GeoTrellis catalog.
    Unlike other functions in this module, this will not return a RDD, but rather
    GeoPySpark formatted tile. This is the function to use when creating a tile server.

    A tile can be read from various backends. These are the ones that are currently supported:
        Local Filesystem
        HDFS
        S3
        Cassandra
        HBase
        Accumulo

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        uri (str): The Uniform Resource Identifier used to point towards the desired GeoTrellis
            catalog to be read from. The shape of this string varies depending on backend.

            Example uris for each backend:
                Local Filesystem: file://my_folder/my_catalog/
                HDFS: hdfs://my_folder/my_catalog/
                S3: s3://my_bucket/my_catalog/
                Cassandra: cassandra:name?username=user&password=pass&host=host1&keyspace=key&table=table
                HBase: hbase://zoo1, zoo2: port/table
                Accumulo: accumulo://username:password/zoo1, zoo2/instance/table
        layer_name (str): The name of the GeoTrellis catalog to be read from.
        layer_zoom (int): The zoom level of the layer that is to be read.
        col (int): The col number of the tile within the layout. Cols run east to west.
        row (int): The row number of the tile within the layout. Row run north to south.
        zdt (str): The Zone-Date-Time string of the tile. The string must be in a valid date-time
            format. This parameter is only used when querying spatial-temporal data. The default
            value is, None. If None, then only the spatial area will be queried.
        options (dict, optional): Additional parameters for reading the tile for specific backends.
            The dictionary is only used for Cassandra and HBase, no other backend requires this
            to be set.

            Fields that can be set for Cassandra:
                replicationStrategy (str, optional): If not specified, then 'SimpleStrategy' will
                    be used.
                replicationFactor (int, optional): If not specified, then 1 will be used.
                localDc (str, optional): If not specified, then 'datacenter1' will be used.
                usedHostsPerRemoteDc (int, optional): If not specified, then 0 will be used.
                allowRemoteDCsForLocalConsistencyLevel (int, optional): If you'd like this feature,
                    then the value would be 1, Otherwise, the value should be 0. If not specified,
                    then 0 will be used.

            Fields that can be set for HBase:
                master (str, optional): If not specified, then 'null' will be used.
        **kwargs: The optional parameters can also be set as keywords arguments. The keywords must
            be in camel case. If both options and keywords are set, then the options will be used.

    Returns:
        dict: A dictionary that contains the tile tile data.

            The fields to represent the tile:
                data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                    Note, even if the data was originally singleband, it will be reformatted as
                    a multiband tile and read and saved as such.
                no_data_value (optional): The no data value of the tile. Can be a range of
                    types including None.
    """

    if options:
        options = options
    elif kwargs:
        options = kwargs
    else:
        options = {}

    _construct_catalog(geopysc, uri, options)

    builds = _mapped_builds[uri]

    if not zdt:
        zdt = ""

    key = geopysc.map_key_input(rdd_type, True)

    tup = builds.value_reader.readTile(key,
                                       layer_name,
                                       layer_zoom,
                                       col,
                                       row,
                                       zdt)

    ser = geopysc.create_value_serializer(tup._2(), TILE)

    if uri not in _mapped_serializers:
        _mapped_serializers[uri] = ser

    return ser.loads(tup._1())[0]

def query(geopysc,
          rdd_type,
          uri,
          layer_name,
          layer_zoom,
          intersects,
          time_intervals=None,
          options=None,
          **kwargs):

    """Queries a single, zoom layer from a GeoTrellis catalog given spatial and/or time parameters.
    Unlike read, this method will only return part of the layer that intersects the specified
    region. However, the whole layer could still be read in if no area/time has been set, or
    if the querried region contains the entire layer.

    A layer can be queried from various backends. These are the ones that are currently supported:
        Local Filesystem
        HDFS
        S3
        Cassandra
        HBase
        Accumulo

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same saptial type.
        uri (str): The Uniform Resource Identifier used to point towards the desired GeoTrellis
            catalog to be read from. The shape of this string varies depending on backend.

            Example uris for each backend:
                Local Filesystem: file://my_folder/my_catalog/
                HDFS: hdfs://my_folder/my_catalog/
                S3: s3://my_bucket/my_catalog/
                Cassandra: cassandra:name?username=user&password=pass&host=host1&keyspace=key&table=table
                HBase: hbase://zoo1, zoo2: port/table
                Accumulo: accumulo://username:password/zoo1, zoo2/instance/table
        layer_name (str): The name of the GeoTrellis catalog to be querried.
        layer_zoom (int): The zoom level of the layer that is to be querried.
        intersects (str, Polygon): The desired spatial area to be returned. Can either be a string
            or a shapely Polygon. If the value is a string, it must be the WKT string, geometry
            format.

            The types of Polygons supported:
                Point
                Polygon
                MultiPolygon

            Note, only layers that were made from spatial, singleband GeoTiffs can query a Point.
            All other types are restricted to Polygon and MulitPolygon.
        time_intervals (list, optional): A list of strings that time intervals to query.
            The strings must be in a valid date-time format. This parameter is only used when
            querying spatial-temporal data. The default value is, None. If None, then only the
            spatial area will be querried.
        options (dict, optional): Additional parameters for querying the tile for specific backends.
            The dictioanry is only used for Cassandra and HBase, no other backend requires this
            to be set.

            Fields that can be set for Cassandra:
                replicationStrategy (str, optional): If not specified, then 'SimpleStrategy' will
                    be used.
                replicationFactor (int, optional): If not specified, then 1 will be used.
                localDc (str, optional): If not specified, then 'datacenter1' will be used.
                usedHostsPerRemoteDc (int, optional): If not specified, then 0 will be used.
                allowRemoteDCsForLocalConsistencyLevel (int, optional): If you'd like this feature,
                    then the value would be 1, Otherwise, the value should be 0. If not specified,
                    then 0 will be used.

            Fields that can be set for HBase:
                master (str, optional): If not specified, then 'null' will be used.
        **kwargs: The optional parameters can also be set as keywords arguements. The keywords must
            be in camel case. If both options and keywords are set, then the options will be used.
    Returns:
        RDD: A RDD that contains tuples of dictionaries, (key, tile).
            key (dict): The index of the tile within the layer. There are two different types
                of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys deal with data that have just
                a spatial component, whereas SpaceTimeKeys are for data with both a spatial and
                time component.

                Both SpatialKeys and SpaceTimeKeys share these fields:
                    col (int): The column number of the grid, runs east to west.
                    row (int): The row number of the grid, runs north to south.

                SpaceTimeKeys also have an additional field:
                    instant (int): The time stamp of the tile.
            tile (dict): The data of the tile.

                The fields to represent the tile:
                    data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                        Note, even if the data was originally singleband, it will be reformatted as
                        a multiband tile and read and saved as such.
                    no_data_value (optional): The no data value of the tile. Can be a range of
                        types including None.

    """

    if options:
        options = options
    elif kwargs:
        options = kwargs
    else:
        options = {}

    _construct_catalog(geopysc, uri, options)

    builds = _mapped_builds[uri]

    key = geopysc.map_key_input(rdd_type, True)

    if time_intervals is None:
        time_intervals = []

    if isinstance(intersects, Polygon):
        srdd = builds.reader.query(key,
                                   layer_name,
                                   layer_zoom,
                                   dumps(intersects),
                                   time_intervals)

    elif isinstance(intersects, str):
        srdd = builds.reader.query(key,
                                   layer_name,
                                   layer_zoom,
                                   intersects,
                                   time_intervals)
    else:
        raise Exception("Could not query intersection", intersects)

    return TiledRasterRDD(geopysc, key, srdd)

def write(geopysc,
          rdd_type,
          uri,
          layer_name,
          layer_zoom,
          rdd,
          metadata,
          index_strategy=ZORDER,
          time_unit=None,
          options=None,
          **kwargs):

    """Writes a tile layer to a specified destination.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same saptial type.
        uri (str): The Uniform Resource Identifier used to point towards the desired location for
        the tile layer to written to. The shape of this string varies depending on backend.

            Example uris for each backend:
                Local Filesystem: file://my_folder/my_catalog/
                HDFS: hdfs://my_folder/my_catalog/
                S3: s3://my_bucket/my_catalog/
                Cassandra: cassandra:name?username=user&password=pass&host=host1&keyspace=key&table=table
                HBase: hbase://zoo1, zoo2: port/table
                Accumulo: accumulo://username:password/zoo1, zoo2/instance/table
        layer_name (str): The name of the new, tile layer.
        layer_zoom (int): The zoom level the layer should be saved at.
        rdd (RDD): A RDD that contains tuples of dictionaries, (key, tile).
            key (dict): The index of the tile within the layer. There are two different types
                of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys deal with data that have just
                a spatial component, whereas SpaceTimeKeys are for data with both a spatial and
                time component.

                Both SpatialKeys and SpaceTimeKeys share these fields:
                    col (int): The column number of the grid, runs east to west.
                    row (int): The row number of the grid, runs north to south.

                SpaceTimeKeys also have an additional field:
                    instant (int): The time stamp of the tile.
            tile (dict): The data of the tile.

                The fields to represent the tile:
                    data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                        Note, even if the data was originally singleband, it will be reformatted as
                        a multiband tile and read and saved as such.
                    no_data_value (optional): The no data value of the tile. Can be a range of
                        types including None.
        tile_layer_metadata (dict): The metadata for this tile layer. This provides
            the layout definition that the tiles will be cut to.

            The fields that are used to represent the metadata:
                cellType (str): The value type of every cell within the rasters.
                layoutDefinition (dict): Defines the raster layout of the rasters.

                The fields that are used to represent the layoutDefinition:
                    extent (dict): The area covered by the layout tiles.
                    tileLayout (dict): The tile layout of the rasters.
                extent (dict): The extent that covers the tiles.
                crs (str): The CRS that the rasters are projected in.
                bounds (dict): Represents the positions of the tile layer tiles within a gird.

                    The fields that are used to represent the bounds:
                        minKey (dict): Represents where the tile layer begins in the gird.
                        maxKey (dict): Represents where the tile layer ends in the gird.

                        The fields that are used to represent the minKey and maxKey:
                            col (int): The column number of the grid, runs east to west.
                            row (int): The row number of the grid, runs north to south.
        index_strategy (str): The method used to orginize the saved data. Depending on the type of
            data within the layer, only certain methods are available. The default method used is,
            ZORDER.

            The different indexing methods:
                ZORDER: Works for both spatial and spatial-temporal data.
                HILBERT: Works for both spatial and spatial-temporal data. Currently has a size
                    limitation where the combined resolutions for each index cannot be greater
                    than 64 bits.
                ROWMAJOR: Works only for spatial data. Is the fastest of the three methods,
                    but can provide unreliable locality results.
        time_unit (str, optional): Horallllllllllllllll data should be indexed when saved.
            While this is set to None as default, it must be set if saving spatial-temporal data.
            Depending on the indexing method chosen, different time units are used.

            Time units for ZORDER:
                MILLIS: Index data by milliseconds.
                SECONDS: Index data by seconds.
                MINUTES: Index data by minutes.
                HOURS: Index data by hours.
                DAYS: Index data by days.
                MONTHS: Index data by months.
                YEARS: Index data by years.

            Time unit for HILBERT:
                The time unit must be in this format: 'min_date, max_date, resolution'.
                Where 'min_date' is the starting date, 'max_date' is the ending date,
                and 'resolution' is the temporal resolution. Both 'min_date' and 'max_date'
                must be in a valid date-time format.

        options (dict, optional): Additional parameters for writing the layer for specific
            backends. The dictioanry is only used for Cassandra and HBase, no other backend
            requires this to be set.

            Fields that can be set for Cassandra:
                replicationStrategy (str, optional): If not specified, then 'SimpleStrategy' will
                    be used.
                replicationFactor (int, optional): If not specified, then 1 will be used.
                localDc (str, optional): If not specified, then 'datacenter1' will be used.
                usedHostsPerRemoteDc (int, optional): If not specified, then 0 will be used.
                allowRemoteDCsForLocalConsistencyLevel (int, optional): If you'd like this feature,
                    then the value would be 1, Otherwise, the value should be 0. If not specified,
                    then 0 will be used.

            Fields that can be set for HBase:
                master (str, optional): If not specified, then 'null' will be used.
        **kwargs: The optional parameters can also be set as keywords arguements. The keywords must
            be in camel case. If both options and keywords are set, then the options will be used.
    """

    if options:
        options = options
    elif kwargs:
        options = kwargs
    else:
        options = {}

    _construct_catalog(geopysc, uri, options)

    builds = _mapped_builds[uri]

    key = geopysc.map_key_input(rdd_type, True)

    schema = geopysc.create_schema(key)

    if not time_unit:
        time_unit = ""

    builds.writer.write(key,
                        layer_name,
                        layer_zoom,
                        rdd._jrdd,
                        schema,
                        json.dumps(metadata),
                        time_unit,
                        index_strategy)
