"""Methods for reading, querying, and saving tile layers to and from GeoTrellis Catalogs.
"""

import json
from collections import namedtuple
from urllib.parse import urlparse

from geopyspark import map_key_input
from geopyspark.geotrellis.protobufcodecs import multibandtile_decoder
from geopyspark.geotrellis import Metadata, Extent, deprecated
from geopyspark.geotrellis.layer import TiledRasterLayer
from geopyspark.geotrellis.constants import TILE, ZORDER, SPATIAL

from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.wkt import dumps
import shapely.wkb


_mapped_cached = {}
_mapped_serializers = {}
_cached = namedtuple('Cached', ('store', 'reader', 'value_reader', 'writer'))

_mapped_bounds = {}


def _construct_catalog(pysc, new_uri, options):
    if new_uri not in _mapped_cached:

        store_factory = pysc._gateway.jvm.geopyspark.geotrellis.io.AttributeStoreFactory
        reader_factory = pysc._gateway.jvm.geopyspark.geotrellis.io.LayerReaderFactory
        value_reader_factory = pysc._gateway.jvm.geopyspark.geotrellis.io.ValueReaderFactory
        writer_factory = pysc._gateway.jvm.geopyspark.geotrellis.io.LayerWriterFactory

        parsed_uri = urlparse(new_uri)
        backend = parsed_uri.scheme

        if backend == 'hdfs':
            store = store_factory.buildHadoop(new_uri, pysc._jsc.sc())
            reader = reader_factory.buildHadoop(store, pysc._jsc.sc())
            value_reader = value_reader_factory.buildHadoop(store)
            writer = writer_factory.buildHadoop(store)

        elif backend == 'file':
            store = store_factory.buildFile(new_uri[7:])
            reader = reader_factory.buildFile(store, pysc._jsc.sc())
            value_reader = value_reader_factory.buildFile(store)
            writer = writer_factory.buildFile(store)

        elif backend == 's3':
            store = store_factory.buildS3(parsed_uri.netloc, parsed_uri.path[1:])
            reader = reader_factory.buildS3(store, pysc._jsc.sc())
            value_reader = value_reader_factory.buildS3(store)
            writer = writer_factory.buildS3(store)

        elif backend == 'cassandra':
            parameters = parsed_uri.query.split('&')
            parameter_dict = {}

            for param in parameters:
                split_param = param.split('=', 1)
                parameter_dict[split_param[0]] = split_param[1]

            store = store_factory.buildCassandra(
                parameter_dict['host'],
                parameter_dict['username'],
                parameter_dict['password'],
                parameter_dict['keyspace'],
                parameter_dict['table'],
                options)

            reader = reader_factory.buildCassandra(store, pysc._jsc.sc())
            value_reader = value_reader_factory.buildCassandra(store)
            writer = writer_factory.buildCassandra(store,
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

            store = store_factory.buildHBase(zookeepers, master, port, table)
            reader = reader_factory.buildHBase(store, pysc._jsc.sc())
            value_reader = value_reader_factory.buildHBase(store)
            writer = writer_factory.buildHBase(store, table)

        elif backend == 'accumulo':

            # The assumed uri looks like: accumulo://username:password/zoo1, zoo2/instance/table
            (user, password) = parsed_uri.netloc.split(':')
            split_parameters = parsed_uri.path.split('/')[1:]

            store = store_factory.buildAccumulo(split_parameters[0],
                                                split_parameters[1],
                                                user,
                                                password,
                                                split_parameters[2])

            reader = reader_factory.buildAccumulo(split_parameters[1],
                                                  store,
                                                  pysc._jsc.sc())

            value_reader = value_reader_factory.buildAccumulo(store)

            writer = writer_factory.buildAccumulo(split_parameters[1],
                                                  store,
                                                  split_parameters[2])

        else:
            raise ValueError("Cannot find Attribute Store for", backend)

        _mapped_cached[new_uri] = _cached(store=store,
                                          reader=reader,
                                          value_reader=value_reader,
                                          writer=writer)

def _in_bounds(pysc, rdd_type, uri, layer_name, zoom_level, col, row):
    if (layer_name, zoom_level) not in _mapped_bounds:
        layer_metadata = read_layer_metadata(pysc, rdd_type, uri, layer_name, zoom_level)
        bounds = layer_metadata.bounds
        _mapped_bounds[(layer_name, zoom_level)] = bounds
    else:
        bounds = _mapped_bounds[(layer_name, zoom_level)]

    mins = col < bounds.minKey.col or row < bounds.minKey.row
    maxs = col > bounds.maxKey.col or row > bounds.maxKey.row

    if mins or maxs:
        return False
    else:
        return True


def read_layer_metadata(pysc,
                        rdd_type,
                        uri,
                        layer_name,
                        layer_zoom,
                        options=None,
                        **kwargs):
    """Reads the metadata from a saved layer without reading in the whole layer.

    Args:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: ``SPATIAL`` and ``SPACETIME``.
        uri (str): The Uniform Resource Identifier used to point towards the desired GeoTrellis
            catalog to be read from. The shape of this string varies depending on backend.
        layer_name (str): The name of the GeoTrellis catalog to be read from.
        layer_zoom (int): The zoom level of the layer that is to be read.
        options (dict, optional): Additional parameters for reading the layer for specific backends.
            The dictionary is only used for ``Cassandra`` and ``HBase``, no other backend requires
            this to be set.
        numPartitions (int, optional): Sets RDD partition count when reading from catalog.
        **kwargs: The optional parameters can also be set as keywords arguments. The keywords must
            be in camel case. If both options and keywords are set, then the options will be used.

    Returns:
        :class:`~geopyspark.geotrellis.Metadata`
    """

    if options:
        options = options
    elif kwargs:
        options = kwargs
    else:
        options = {}

    _construct_catalog(pysc, uri, options)
    cached = _mapped_cached[uri]

    if rdd_type == SPATIAL:
        metadata = cached.store.metadataSpatial(layer_name, layer_zoom)
    else:
        metadata = cached.store.metadataSpaceTime(layer_name, layer_zoom)

    return Metadata.from_dict(json.loads(metadata))

def get_layer_ids(pysc,
                  uri,
                  options=None,
                  **kwargs):
    """Returns a list of all of the layer ids in the selected catalog as dicts that contain the
    name and zoom of a given layer.

    Args:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        uri (str): The Uniform Resource Identifier used to point towards the desired GeoTrellis
            catalog to be read from. The shape of this string varies depending on backend.
        options (dict, optional): Additional parameters for reading the layer for specific backends.
            The dictionary is only used for Cassandra and HBase, no other backend requires this
            to be set.
        **kwargs: The optional parameters can also be set as keywords arguments. The keywords must
            be in camel case. If both options and keywords are set, then the options will be used.

    Returns:
        [layerIds]

        Where ``layerIds`` is a ``dict`` with the following fields:
            - **name** (str): The name of the layer
            - **zoom** (int): The zoom level of the given layer.
    """

    if options:
        options = options
    elif kwargs:
        options = kwargs
    else:
        options = {}

    _construct_catalog(pysc, uri, options)
    cached = _mapped_cached[uri]

    return list(cached.reader.layerIds())

@deprecated
def read(pysc,
         rdd_type,
         uri,
         layer_name,
         layer_zoom,
         options=None,
         numPartitions=None,
         **kwargs):

    """Deprecated in favor of geopyspark.geotrellis.catalog.query."""

    return query(pysc, rdd_type, uri, layer_name, layer_zoom, options=options,
                 numPartitions=numPartitions)

def read_value(pysc,
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
    Unlike other functions in this module, this will not return a ``TiledRasterLayer``, but rather a
    GeoPySpark formatted raster. This is the function to use when creating a tile server.

    Note:
        When requesting a tile that does not exist, ``None`` will be returned.

    Args:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: ``SPATIAL`` and ``SPACETIME``.
        uri (str): The Uniform Resource Identifier used to point towards the desired GeoTrellis
            catalog to be read from. The shape of this string varies depending on backend.
        layer_name (str): The name of the GeoTrellis catalog to be read from.
        layer_zoom (int): The zoom level of the layer that is to be read.
        col (int): The col number of the tile within the layout. Cols run east to west.
        row (int): The row number of the tile within the layout. Row run north to south.
        zdt (str): The Zone-Date-Time string of the tile. The string must be in a valid date-time
            format. This parameter is only used when querying spatial-temporal data. The default
            value is, None. If None, then only the spatial area will be queried.
        options (dict, optional): Additional parameters for reading the tile for specific backends.
            The dictionary is only used for ``Cassandra`` and ``HBase``, no other backend requires
            this to be set.
        **kwargs: The optional parameters can also be set as keywords arguments. The keywords must
            be in camel case. If both options and keywords are set, then the options will be used.

    Returns:
        :ref:`raster` or ``None``
    """

    if not _in_bounds(pysc, rdd_type, uri, layer_name, layer_zoom, col, row):
        return None
    else:
        if options:
            options = options
        elif kwargs:
            options = kwargs
        else:
            options = {}

        if uri not in _mapped_cached:
            _construct_catalog(pysc, uri, options)

        cached = _mapped_cached[uri]

        if not zdt:
            zdt = ""

        key = map_key_input(rdd_type, True)

        values = cached.value_reader.readTile(key,
                                              layer_name,
                                              layer_zoom,
                                              col,
                                              row,
                                              zdt)

        return multibandtile_decoder(values)

def query(pysc,
          rdd_type,
          uri,
          layer_name,
          layer_zoom,
          query_geom=None,
          time_intervals=None,
          query_proj=None,
          options=None,
          numPartitions=None,
          **kwargs):

    """Queries a single, zoom layer from a GeoTrellis catalog given spatial and/or time parameters.
    Unlike read, this method will only return part of the layer that intersects the specified
    region.

    Note:
        The whole layer could still be read in if ``intersects`` and/or ``time_intervals`` have not
        been set, or if the querried region contains the entire layer.

    Args:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: ``SPATIAL`` and ``SPACETIME``. Note: All of the
            GeoTiffs must have the same saptial type.
        uri (str): The Uniform Resource Identifier used to point towards the desired GeoTrellis
            catalog to be read from. The shape of this string varies depending on backend.
        layer_name (str): The name of the GeoTrellis catalog to be querried.
        layer_zoom (int): The zoom level of the layer that is to be querried.
        query_geom (bytes or shapely.geometry or :class:`~geopyspark.geotrellis.data_structures.Extent`, Optional):
            The desired spatial area to be returned. Can either be a string, a shapely geometry, or
            instance of ``Extent``, or a WKB verson of the geometry.

            Note:
                Not all shapely geometires are supported. The following is are the types that are
                supported:
                * Point
                * Polygon
                * MultiPolygon

            Note:
                Only layers that were made from spatial, singleband GeoTiffs can query a ``Point``.
                All other types are restricted to ``Polygon`` and ``MulitPolygon``.

            If not specified, then the entire layer will be read.
        time_intervals (list, optional): A list of strings that time intervals to query.
            The strings must be in a valid date-time format. This parameter is only used when
            querying spatial-temporal data. The default value is, None. If None, then only the
            spatial area will be querried.
        options (dict, optional): Additional parameters for querying the tile for specific backends.
            The dictioanry is only used for ``Cassandra`` and ``HBase``, no other backend requires
            this to be set.
        numPartitions (int, optional): Sets RDD partition count when reading from catalog.
        **kwargs: The optional parameters can also be set as keywords arguements. The keywords must
            be in camel case. If both options and keywords are set, then the options will be used.

    Returns:
        :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`

    """
    if options:
        options = options
    elif kwargs:
        options = kwargs
    else:
        options = {}

    _construct_catalog(pysc, uri, options)

    cached = _mapped_cached[uri]

    key = map_key_input(rdd_type, True)

    if numPartitions is None:
        numPartitions = pysc.defaultMinPartitions

    if not query_geom:
        srdd = cached.reader.read(key, layer_name, layer_zoom, numPartitions)
        return TiledRasterLayer(pysc, rdd_type, srdd)

    else:
        if time_intervals is None:
            time_intervals = []

        if query_proj is None:
            query_proj = ""
        if isinstance(query_proj, int):
            query_proj = "EPSG:" + str(query_proj)

        if isinstance(query_geom, (Polygon, MultiPolygon, Point)):
            srdd = cached.reader.query(key,
                                       layer_name,
                                       layer_zoom,
                                       shapely.wkb.dumps(query_geom),
                                       time_intervals,
                                       query_proj,
                                       numPartitions)

        elif isinstance(query_geom, Extent):
            srdd = cached.reader.query(key,
                                       layer_name,
                                       layer_zoom,
                                       shapely.wkb.dumps(query_geom.to_poly),
                                       time_intervals,
                                       query_proj,
                                       numPartitions)

        elif isinstance(query_geom, bytes):
            srdd = cached.reader.query(key,
                                       layer_name,
                                       layer_zoom,
                                       query_geom,
                                       time_intervals,
                                       query_proj,
                                       numPartitions)
        else:
            raise TypeError("Could not query intersection", query_geom)

        return TiledRasterLayer(pysc, rdd_type, srdd)

def write(uri,
          layer_name,
          tiled_raster_rdd,
          index_strategy=ZORDER,
          time_unit=None,
          options=None,
          **kwargs):

    """Writes a tile layer to a specified destination.

    Args:
        uri (str): The Uniform Resource Identifier used to point towards the desired location for
            the tile layer to written to. The shape of this string varies depending on backend.
        layer_name (str): The name of the new, tile layer.
        layer_zoom (int): The zoom level the layer should be saved at.
        tiled_raster_rdd (:class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`): The
            ``TiledRasterLayer`` to be saved.
        index_strategy (str): The method used to orginize the saved data. Depending on the type of
            data within the layer, only certain methods are available. The default method used is,
            ``ZORDER``.
        time_unit (str, optional): Which time unit should be used when saving spatial-temporal data.
            While this is set to None as default, it must be set if saving spatial-temporal data.
            Depending on the indexing method chosen, different time units are used.
        options (dict, optional): Additional parameters for writing the layer for specific
            backends. The dictioanry is only used for ``Cassandra`` and ``HBase``, no other backend
            requires this to be set.
        **kwargs: The optional parameters can also be set as keywords arguements. The keywords must
            be in camel case. If both options and keywords are set, then the options will be used.

    """
    if options:
        options = options
    elif kwargs:
        options = kwargs
    else:
        options = {}

    _construct_catalog(tiled_raster_rdd.pysc, uri, options)

    cached = _mapped_cached[uri]

    if not time_unit:
        time_unit = ""

    if tiled_raster_rdd.rdd_type == SPATIAL:
        cached.writer.writeSpatial(layer_name,
                                   tiled_raster_rdd.srdd,
                                   index_strategy)
    else:
        cached.writer.writeTemporal(layer_name,
                                    tiled_raster_rdd.srdd,
                                    time_unit,
                                    index_strategy)
