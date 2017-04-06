"""Methods for working with, and creating tile layers.

A tile layer a is a RDD of tuples that contain tuples of (K, V) with Metadata. Where K is an index
that represents where V is within the overall tile layout. V is always a tile that contains the
spatial/spatial-temporal information of that area. Metadata contains the projection, layout, and
area information of the layer.
"""
import json
import shapely.wkt

from geopyspark.avroserializer import AvroSerializer
from geopyspark.constants import NEARESTNEIGHBOR, TILE


def _convert_to_java_rdd(geopysc, rdd_type, raster_rdd):
    if isinstance(raster_rdd._jrdd_deserializer.serializer, AvroSerializer):
        schema = raster_rdd._jrdd_deserializer.serializer.schema_string

        return (raster_rdd._jrdd, schema)
    else:
        schema = geopysc.create_schema(rdd_type)
        ser = geopysc.create_tuple_serializer(schema, key_type=None, value_type=TILE)
        reserialized_rdd = raster_rdd._reserialize(ser)

        return (reserialized_rdd._jrdd, schema)

def collect_metadata(geopysc,
                     rdd_type,
                     raster_rdd,
                     layout_extent,
                     tile_layout,
                     output_crs=None):

    """Collects the metadata of an RDD.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants, SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        raster_rdd(RDD): An RDD that contains tuples of (projection_info, tile).
            projection_info (dict): Contains the area on Earth the tile represents in addition to
                the tile's projection information. There are two different types of projection_info,
                ProjectedExtent and TemporalProjectedExtent. The first deals with data that
                only has a spatial component, while the latter has both a spatial and temporal
                attributes.

                Both ProjectedExtent and TemporalProjectedExtent share these fields:
                    extent (dict): The 'Bounding Box' of an area on Earth that is
                        contained within the GeoTiff.

                        The fields that are used to represent the layout_extent:
                            xmin (double): The bottom, left corner of the area.
                            ymin (double): The top, left corner of the area.
                            xmax (double): The bottom, right corner of the area.
                            ymax (double): The top, right corner of the area.

                    crs (str): The CRS that the rasters are projected in.

                TemporalProjectedExtent also have an additional field:
                    instant (int): The time stamp of the tile.

            tile (dict): The data of the tile.

                The fields that represent the tile:
                    data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                        Note, even if the data is a singleband GeoTiff, it will be reformatted as
                        a multiband tile and read and saved as such.
                    no_data_value (optional): The no data value of the tile. Can be a range of
                        types, including None.
        layout_extent (dict): The new 'Bounding Box' that the this layer will cover.
        tile_layout (dict): How the tiles are laid out over the area.

            The fields that are used to represent the tile_layout:
                tileCols (int): The number of columns of tiles that runs east to west.
                tileRows (int): The number of rows of tiles that runs north to south.
                tileCols (int): The number of pixel cols in tile that runs east to west.
                tileRows (int): The number of pixel rows in tile that runs north to south.
        output_crs (str, optional): The CRS that the metadata should be
            represented in. Must be in well-known name format. If None, then the GeoTiffs'
            original CRS will be used.

    Returns:
        dict: The dictionary representation of the RDD's metadata.
            The fields that are used to represent the metadata:
                cellType (str): The value type of every cell within the rasters.
                layoutDefinition (dict): Defines the raster layout of the rasters.

                The fields that are used to represent the layoutDefinition:
                    extent (dict): The area covered by the layout tiles.
                    tileLayout (dict): The tile layout of the rasters.
                extent (dict): The extent that covers the tiles.
                crs (str): The CRS that the rasters are projected in.
                bounds (dict): Represents the positions of the tile layer's tiles within a gird.
                    These positions are represented by keys. There are two different types of keys,
                    SpatialKeys and SpaceTimeKeys. SpatialKeys are for data that only have a
                    spatial component while SpaceTimeKeys are for data with both spatial and
                    temporal components.

                    Both SpatialKeys and SpaceTimeKeys share these fields:
                        The fields that are used to represent the bounds:
                            minKey (dict): Represents where the tile layer begins in the gird.
                            maxKey (dict): Represents where the tile layer ends in the gird.

                            The fields that are used to represent the minKey and maxKey:
                                col (int): The column number of the grid, runs east to west.
                                row (int): The row number of the grid, runs north to south.

                    SpaceTimeKeys also have an additional field:
                        instant (int): The time stamp of the tile.
    """

    metadata_wrapper = geopysc._tile_layer_metadata_collecter
    key = geopysc.map_key_input(rdd_type, False)

    (java_rdd, schema) = _convert_to_java_rdd(geopysc, key, raster_rdd)

    if output_crs:
        output_crs = output_crs
    else:
        output_crs = ""

    metadata = metadata_wrapper.collectPythonMetadata(key,
                                                      java_rdd,
                                                      schema,
                                                      layout_extent,
                                                      tile_layout,
                                                      output_crs)

    return json.loads(metadata)


def collect_pyramid_metadata(geopysc,
                             rdd_type,
                             raster_rdd,
                             crs,
                             tile_size,
                             resolution_threshold=0.1,
                             max_zoom=12,
                             output_crs=None):

    """Collects the metadata of an RDD as well as the zoom level of the RDD.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        raster_rdd(RDD): An RDD that contains tuples of (projection_info, tile).
            projection_info (dict): Contains the area on Earth the tile represents in addition to
                the tile's projection information. There are two different types of projection_info,
                ProjectedExtent and TemporalProjectedExtent. The first deals with data that
                only has a spatial component, while the latter has both a spatial and temporal
                attributes.

                Both ProjectedExtent and TemporalProjectedExtent share these fields:
                    extent (dict): The 'Bounding Box' of an area on Earth that is
                        contained within the GeoTiff.

                        The fields that are used to represent the layout_extent:
                            xmin (double): The bottom, left corner of the area.
                            ymin (double): The top, left corner of the area.
                            xmax (double): The bottom, right corner of the area.
                            ymax (double): The top, right corner of the area.

                    crs (str): The CRS that the rasters are projected in.

                TemporalProjectedExtent also have an additional field:
                    instant (int): The time stamp of the tile.

            tile (dict): The data of the tile.

                The fields that represent the tile:
                    data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                        Note, even if the data is a singleband GeoTiff, it will be reformatted as
                        a multiband tile and read and saved as such.
                    no_data_value (optional): The no data value of the tile. Can be a range of
                        types, including None.
        crs (str): The CRS that the tiles within the RDD are in.
            The CRS must be in the well-known name format.
        tile_size (int): The size of the each tile in the RDD in terms of
            pixels. Thus, if each tile within a RDD is 256x256 then the
            tile_size will be 256. Note: All tiles within the RDD must be of the
            same size.
        resolution_threshold (double, optional): The percentage difference between
            the cell size and zoom level as well as the resolution difference between
            a given zoom level, and the next that is tolerated to snap to the lower-resolution
            zoom level. If not specified, the default value is: 0.1.
        max_zoom (int, optional): The max level this tile layer can go to.
            If not specified, the default max_zoom is: 12.
        output_crs (str, optional): The CRS that the metadata should be
            represented in. Must be in well-known name format. If None, then the GeoTiffs'
            original CRS will be used.

    Returns:
        tup: A tuple that contains the zoom level and the metadata for the tile layer.
            int: The zoom level of the tile layer.
            dict: The dictionary representation of the RDD's metadata.
                The fields that are used to represent the metadata:
                    cellType (str): The value type of every cell within the rasters.
                    layoutDefinition (dict): Defines the raster layout of the rasters.

                    The fields that are used to represent the layoutDefinition:
                        extent (dict): The area covered by the layout tiles.
                        tileLayout (dict): The tile layout of the rasters.
                    extent (dict): The extent that covers the tiles.
                    crs (str): The CRS that the rasters are projected in.
                    bounds (dict): Represents the positions of the tile layer's tiles within a gird.
                        These positions are represented by keys. There are two different types of
                        keys, SpatialKeys and SpaceTimeKeys. SpatialKeys are for data that only
                        have a spatial component while SpaceTimeKeys are for data with both
                        spatial and temporal components.

                        Both SpatialKeys and SpaceTimeKeys share these fields:
                            The fields that are used to represent the bounds:
                                minKey (dict): Represents where the tile layer begins in the gird.
                                maxKey (dict): Represents where the tile layer ends in the gird.

                                The fields that are used to represent the minKey and maxKey:
                                    col (int): The column number of the grid, runs east to west.
                                    row (int): The row number of the grid, runs north to south.

                        SpaceTimeKeys also have an additional field:
                            instant (int): The time stamp of the tile.
    """

    metadata_wrapper = geopysc._tile_layer_metadata_collecter
    key = geopysc.map_key_input(rdd_type, False)

    (java_rdd, schema) = _convert_to_java_rdd(geopysc, key, raster_rdd)

    if output_crs:
        output_crs = output_crs
    else:
        output_crs = ""

    result = metadata_wrapper.collectPythonMetadata(key,
                                                    java_rdd,
                                                    schema,
                                                    crs,
                                                    tile_size,
                                                    resolution_threshold,
                                                    max_zoom,
                                                    output_crs)

    return (result._1(), json.loads(result._2()))

def collect_floating_metadata(geopysc,
                              rdd_type,
                              raster_rdd,
                              tile_cols,
                              tile_rows,
                              output_crs=None):

    """Collects the metadata of an RDD as well as the zoom level of the RDD.

    TODO: Finish the rest of the docs.

    """

    if output_crs:
        output_crs = output_crs
    else:
        output_crs = ""

    metadata_wrapper = geopysc._tile_layer_metadata_collecter
    key = geopysc.map_key_input(rdd_type, False)

    (java_rdd, schema) = _convert_to_java_rdd(geopysc, key, raster_rdd)

    result = metadata_wrapper.collectPythonMetadata(key,
                                                    java_rdd,
                                                    schema,
                                                    tile_cols,
                                                    tile_rows,
                                                    output_crs)
    return (result._1(), json.loads(result._2()))

def reproject(geopysc,
              raster_rdd,
              dest_crs,
              resample_method=NEARESTNEIGHBOR,
              error_threshold=0.125):

    """Reprojects the tiles within a RDD to a new projection.

    TODO: Write the remaining docs.

    """

    reproject_wrapper = geopysc._rdd_reprojector
    key = geopysc.map_key_input(SPATIAL, False)

    (java_rdd, schema) = _convert_to_java_rdd(geopysc, key, raster_rdd)

    result = reproject_wrapper.reproject(java_rdd,
                                         schema,
                                         dest_crs,
                                         resample_method,
                                         error_threshold)

    (rdd, returned_schema) = (result._1()._1(), result._1()._2())
    ser = geopysc.create_tuple_serializer(returned_schema, value_type=TILE)
    returned_rdd = geopysc.create_python_rdd(rdd, ser)

    return (returned_rdd, json.loads(result._2()))

def reproject_to_layout(geopysc,
                        rdd_type,
                        keyed_rdd,
                        tile_layer_metadata,
                        dest_crs,
                        layer_layout=None,
                        match_layer_extent=False,
                        resample_method=NEARESTNEIGHBOR,
                        **kwargs):

    """Reprojects the tiles within a RDD to a new projection.

    The new RDD will have tiles that are laid according to the the layout definition
    within the metadata. This function is used when the RDD has no corresponding zoom
    (ie. is not a layer within a pyramid).

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        tile_layer_metadata (dict): The metadata for this tile layer. This provides
            the information needed to resample the old tiles and create new ones.

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
        dest_crs (str): The CRS that the tiles should be reprojected to. Must be in well-known name
            format. This can be same,or a different than what's in the tile_layer_metadata.
        match_layer_extent (bool): Should the reprojection attempt to match the total layer's
            extent. Defaults to False. This should only be used with small extents, as seems can
            occur if the extent is too large.

    Returns:
        tuple: A tuple containing (reprojected_rdd, metadata).
            projected_rdd (RDD): A RDD that contains data only for that layer represented as
                tuples of dictionaries.

                key (dict): The index of the tile within the layer. There are two different
                    types of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys deal with data that
                    have just a spatial component, whereas SpaceTimeKeys are for data with both a
                    spatial and time component.

                    Both SpatialKeys and SpaceTimeKeys share these fields:
                        col (int): The column number of the grid, runs east to west.
                        row (int): The row number of the grid, runs north to south.

                    SpaceTimeKeys also have an additional field:
                        instant (int): The time stamp of the tile.
                tile (dict): The data of the tile.

                    The fields to represent the tile:
                        data (np.ndarray): The tile data itself is represented as a 3D, numpy
                            array.  Note, even if the data was originally singleband, it will
                            be reformatted as a multiband tile and read and saved as such.
                        no_data_value (optional): The no data value of the tile. Can be a range of
                            types including None.
            metadata (dict): The metadata for the RDD.
                dict: The dictionary representation of the RDD's metadata.
                    The fields that are used to represent the metadata:
                        cellType (str): The value type of every cell within the rasters.
                        layoutDefinition (dict): Defines the raster layout of the rasters.

                        The fields that are used to represent the layoutDefinition:
                            extent (dict): The area covered by the layout tiles.
                            tileLayout (dict): The tile layout of the rasters.
                        extent (dict): The extent that covers the tiles.
                        crs (str): The CRS that the rasters are projected in.
                        bounds (dict): Represents the positions of the tile layer's tiles within
                            a gird.  These positions are represented by keys. There are two
                            different types of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys are
                            for data that only have a spatial component while SpaceTimeKeys are for
                            data with both spatial and temporal components.

                            Both SpatialKeys and SpaceTimeKeys share these fields:
                                The fields that are used to represent the bounds:
                                    minKey (dict): Represents where the tile layer begins in the
                                        gird.
                                    maxKey (dict): Represents where the tile layer ends in the gird.

                                    The fields that are used to represent the minKey and maxKey:
                                        col (int): The column number of the grid, runs east to west.
                                        row (int): The row number of the grid, runs north to south.

                            SpaceTimeKeys also have an additional field:
                                instant (int): The time stamp of the tile.
    """

    if not layer_layout and not kwargs:
        raise Exception("layer_formation needs to be set in order to reproject the RDD")

    if kwargs and not layer_layout:
        layer_layout = kwargs

    reproject_wrapper = geopysc._rdd_reprojector
    key = geopysc.map_key_input(rdd_type, True)

    (java_rdd, schema) = _convert_to_java_rdd(geopysc, key, keyed_rdd)

    if 'tile_layout' and 'layout_extent' in layer_layout:
        result = reproject_wrapper.reproject(key,
                                             java_rdd,
                                             schema,
                                             json.dumps(tile_layer_metadata),
                                             dest_crs,
                                             layer_layout['layout_extent'],
                                             layer_layout['tile_layout'],
                                             resample_method,
                                             match_layer_extent)

    elif 'tile_size' and 'resolution_threshold' in layer_layout:
        result = reproject_wrapper.reproject(key,
                                             java_rdd,
                                             schema,
                                             json.dumps(tile_layer_metadata),
                                             dest_crs,
                                             layer_layout['tile_size'],
                                             layer_layout['resolution_threshold'],
                                             resample_method,
                                             match_layer_extent)
    else:
        result = reproject_wrapper.reproject(key,
                                             java_rdd,
                                             schema,
                                             json.dumps(tile_layer_metadata),
                                             dest_crs,
                                             layer_layout['tile_size'],
                                             resample_method,
                                             match_layer_extent)

    (rdd, returned_schema) = (result._2()._1(), result._2()._2())
    ser = geopysc.create_tuple_serializer(returned_schema, value_type=TILE)
    returned_rdd = geopysc.create_python_rdd(rdd, ser)

    return (result._1(), returned_rdd, json.loads(result._3()))

def cut_tiles(geopysc,
              rdd_type,
              raster_rdd,
              tile_layer_metadata,
              resample_method=NEARESTNEIGHBOR):

    """Cuts the tiles within a RDD to a given tile layout.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        raster_rdd(RDD): An RDD that contains tuples of (projection_info, tile).
            projection_info (dict): Contains the area on Earth the tile represents in addition to
                the tile's projection information. There are two different types of projection_info,
                ProjectedExtent and TemporalProjectedExtent. The first deals with data that
                only has a spatial component, while the latter has both a spatial and temporal
                attributes.

                Both ProjectedExtent and TemporalProjectedExtent share these fields:
                    extent (dict): The 'Bounding Box' of an area on Earth that is
                        contained within the GeoTiff.

                        The fields that are used to represent the layout_extent:
                            xmin (double): The bottom, left corner of the area.
                            ymin (double): The top, left corner of the area.
                            xmax (double): The bottom, right corner of the area.
                            ymax (double): The top, right corner of the area.

                    crs (str): The CRS that the rasters are projected in.

                TemporalProjectedExtent also have an additional field:
                    instant (int): The time stamp of the tile.

            tile (dict): The data of the tile.

                The fields that represent the tile:
                    data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                        Note, even if the data is a singleband GeoTiff, it will be reformatted as
                        a multiband tile and read and saved as such.
                    no_data_value (optional): The no data value of the tile. Can be a range of
                        types, including None.
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
        resample_method (str, optional): The resample method used when creating the resulting
            tiles. If None, the default method is: NEARESTNEIGHBOR.

            The list of supported methods:
                NEARESTNEIGHBOR
                BILINEAR
                CUBICCONVOLUTION
                CUBICSPLINE
                LANCZOS
                AVERAGE
                MODE
                MEDIAN
                MAX
                MIN

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
    tiler_wrapper = geopysc._tile_layer_methods
    key = geopysc.map_key_input(rdd_type, False)

    (java_rdd, schema) = _convert_to_java_rdd(geopysc, key, raster_rdd)

    result = tiler_wrapper.cutTiles(key,
                                    java_rdd,
                                    schema,
                                    json.dumps(tile_layer_metadata),
                                    resample_method)

    ser = geopysc.create_tuple_serializer(result._2(), value_type=TILE)

    return geopysc.create_python_rdd(result._1(), ser)

def tile_to_layout(geopysc,
                   rdd_type,
                   raster_rdd,
                   tile_layer_metadata,
                   resample_method=NEARESTNEIGHBOR):

    """Resamples tiles to a new resolution.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        raster_rdd(RDD): An RDD that contains tuples of (projection_info, tile).
            projection_info (dict): Contains the area on Earth the tile represents in addition to
                the tile's projection information. There are two different types of projection_info,
                ProjectedExtent and TemporalProjectedExtent. The first deals with data that
                only has a spatial component, while the latter has both a spatial and temporal
                attributes.

                Both ProjectedExtent and TemporalProjectedExtent share these fields:
                    extent (dict): The 'Bounding Box' of an area on Earth that is
                        contained within the GeoTiff.

                        The fields that are used to represent the layout_extent:
                            xmin (double): The bottom, left corner of the area.
                            ymin (double): The top, left corner of the area.
                            xmax (double): The bottom, right corner of the area.
                            ymax (double): The top, right corner of the area.

                    crs (str): The CRS that the rasters are projected in.

                TemporalProjectedExtent also have an additional field:
                    instant (int): The time stamp of the tile.

            tile (dict): The data of the tile.

                The fields that represent the tile:
                    data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                        Note, even if the data is a singleband GeoTiff, it will be reformatted as
                        a multiband tile and read and saved as such.
                    no_data_value (optional): The no data value of the tile. Can be a range of
                        types, including None.
        tile_layer_metadata (dict): The metadata for this tile layer. This provides
            the information needed to resample the old tiles and create new ones.

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
        resample_method (str, optional): The resample method used when creating the resulting
            tiles. If None, the default method is: NEARESTNEIGHBOR.

            The list of supported methods:
                NEARESTNEIGHBOR
                BILINEAR
                CUBICCONVOLUTION
                CUBICSPLINE
                LANCZOS
                AVERAGE
                MODE
                MEDIAN
                MAX
                MIN

    """
    tiler_wrapper = geopysc._tile_layer_methods
    key = geopysc.map_key_input(rdd_type, False)

    (java_rdd, schema) = _convert_to_java_rdd(geopysc, key, raster_rdd)

    result = tiler_wrapper.tileToLayout(key,
                                        java_rdd,
                                        schema,
                                        json.dumps(tile_layer_metadata),
                                        resample_method)

    ser = geopysc.create_tuple_serializer(result._2(), value_type=TILE)

    return geopysc.create_python_rdd(result._1(), ser)

def merge_tiles(geopysc,
                rdd_type,
                rdd_1,
                rdd_2):

    """Merges the tiles of two RDDs.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        rdd_1(RDD): An RDD that contains tuples of (projection_info, tile).
            projection_info (dict): Contains the area on Earth the tile represents in addition to
                the tile's projection information. There are two different types of projection_info,
                ProjectedExtent and TemporalProjectedExtent. The first deals with data that
                only has a spatial component, while the latter has both a spatial and temporal
                attributes.

                Both ProjectedExtent and TemporalProjectedExtent share these fields:
                    extent (dict): The 'Bounding Box' of an area on Earth that is
                        contained within the GeoTiff.

                        The fields that are used to represent the layout_extent:
                            xmin (double): The bottom, left corner of the area.
                            ymin (double): The top, left corner of the area.
                            xmax (double): The bottom, right corner of the area.
                            ymax (double): The top, right corner of the area.

                    crs (str): The CRS that the rasters are projected in.

                TemporalProjectedExtent also have an additional field:
                    instant (int): The time stamp of the tile.

            tile (dict): The data of the tile.

                The fields that represent the tile:
                    data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                        Note, even if the data is a singleband GeoTiff, it will be reformatted as
                        a multiband tile and read and saved as such.
                    no_data_value (optional): The no data value of the tile. Can be a range of
                        types, including None.
        rdd_2(RDD): An RDD that contains tuples of (projection_info, tile).
            projection_info (dict): Contains the area on Earth the tile represents in addition to
                the tile's projection information. There are two different types of projection_info,
                ProjectedExtent and TemporalProjectedExtent. The first deals with data that
                only has a spatial component, while the latter has both a spatial and temporal
                attributes.

                Both ProjectedExtent and TemporalProjectedExtent share these fields:
                    extent (dict): The 'Bounding Box' of an area on Earth that is
                        contained within the GeoTiff.

                        The fields that are used to represent the layout_extent:
                            xmin (double): The bottom, left corner of the area.
                            ymin (double): The top, left corner of the area.
                            xmax (double): The bottom, right corner of the area.
                            ymax (double): The top, right corner of the area.

                    crs (str): The CRS that the rasters are projected in.

                TemporalProjectedExtent also have an additional field:
                    instant (int): The time stamp of the tile.

            tile (dict): The data of the tile.

                The fields that represent the tile:
                    data (np.ndarray): The tile data itself is represented as a 3D, numpy array.
                        Note, even if the data is a singleband GeoTiff, it will be reformatted as
                        a multiband tile and read and saved as such.
                    no_data_value (optional): The no data value of the tile. Can be a range of
                        types, including None.

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
    merge_wrapper = geopysc._tile_layer_merge
    key = geopysc.map_key_input(rdd_type, False)

    (java_rdd_1, schema_1) = _convert_to_java_rdd(geopysc, key, rdd_1)
    (java_rdd_2, schema_2) = _convert_to_java_rdd(geopysc, key, rdd_2)

    result = merge_wrapper.merge(key,
                                 java_rdd_1,
                                 schema_1,
                                 java_rdd_2,
                                 schema_2)

    ser = geopysc.create_tuple_serializer(result._2(), value_type=TILE)

    return geopysc.create_python_rdd(result._1(), ser)

def pyramid(geopysc,
            rdd_type,
            base_raster_rdd,
            layer_metadata,
            tile_size,
            start_zoom,
            end_zoom,
            resolution_threshold=0.1,
            resample_method=NEARESTNEIGHBOR):

    """Creates a pyramid layout from a tile layer.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        base_raster_rdd(RDD): A RDD that contains tuples of dictionaries, (key, tile).
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
            the information needed to resample the old tiles and create new ones.

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
        tile_size (int): The size of the each tile in the RDD in terms of
            pixels. Thus, if each tile within a RDD is 256x256 then the
            tile_size will be 256. Note: All tiles within the RDD must be of the
            same size.
        start_zoom (int): The zoom level where the pyramiding should begin. Represents the layer
            that is most zoomed out.
        end_zoom (int): The zoom level where the pyramiding should end. Represents the layer
            that is most zoomed in.
        resolution_threshold (double, optional): The percentage difference between
            the cell size and zoom level as well as the resolution difference between
            a given zoom level, and the next that is tolerated to snap to the lower-resolution
            zoom level. If not specified, the default value is: 0.1.
        resample_method (str, optional): The resample method used when creating the resulting
            tiles. If None, the default method is: NEARESTNEIGHBOR.

            The list of supported methods:
                NEARESTNEIGHBOR
                BILINEAR
                CUBICCONVOLUTION
                CUBICSPLINE
                LANCZOS
                AVERAGE
                MODE
                MEDIAN
                MAX
                MIN

    Returns:
        list: A list of tuples that contain (zoom_level, pyramided_rdd, metadata).
            Each tuple represents a single laye of the pyramid.

            zoom_level (int): Represents the level of the layer.
            pyramided_rdd (RDD): A RDD that contains data only for that layer represented as
                tuples of dictionaries.

                key (dict): The index of the tile within the layer. There are two different
                    types of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys deal with data that
                    have just a spatial component, whereas SpaceTimeKeys are for data with both a
                    spatial and time component.

                    Both SpatialKeys and SpaceTimeKeys share these fields:
                        col (int): The column number of the grid, runs east to west.
                        row (int): The row number of the grid, runs north to south.

                    SpaceTimeKeys also have an additional field:
                        instant (int): The time stamp of the tile.
                tile (dict): The data of the tile.

                    The fields to represent the tile:
                        data (np.ndarray): The tile data itself is represented as a 3D, numpy
                            array.  Note, even if the data was originally singleband, it will
                            be reformatted as a multiband tile and read and saved as such.
                        no_data_value (optional): The no data value of the tile. Can be a range of
                            types including None.
            metadata (dict): The metadata for that layer.
                dict: The dictionary representation of the RDD's metadata.
                    The fields that are used to represent the metadata:
                        cellType (str): The value type of every cell within the rasters.
                        layoutDefinition (dict): Defines the raster layout of the rasters.

                        The fields that are used to represent the layoutDefinition:
                            extent (dict): The area covered by the layout tiles.
                            tileLayout (dict): The tile layout of the rasters.
                        extent (dict): The extent that covers the tiles.
                        crs (str): The CRS that the rasters are projected in.
                        bounds (dict): Represents the positions of the tile layer's tiles within
                            a gird.  These positions are represented by keys. There are two
                            different types of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys are
                            for data that only have a spatial component while SpaceTimeKeys are for
                            data with both spatial and temporal components.

                            Both SpatialKeys and SpaceTimeKeys share these fields:
                                The fields that are used to represent the bounds:
                                    minKey (dict): Represents where the tile layer begins in the
                                        gird.
                                    maxKey (dict): Represents where the tile layer ends in the gird.

                                    The fields that are used to represent the minKey and maxKey:
                                        col (int): The column number of the grid, runs east to west.
                                        row (int): The row number of the grid, runs north to south.

                            SpaceTimeKeys also have an additional field:
                                instant (int): The time stamp of the tile.
    """


    pyramider = geopysc._pyramid_builder
    key = geopysc.map_key_input(rdd_type, True)

    (java_rdd, schema) = _convert_to_java_rdd(geopysc, key, base_raster_rdd)

    result = pyramider.buildPythonPyramid(key,
                                          java_rdd,
                                          schema,
                                          json.dumps(layer_metadata),
                                          tile_size,
                                          resolution_threshold,
                                          start_zoom,
                                          end_zoom,
                                          resample_method)

    def _formatter(tile_layer):
        (rdd, schema) = (tile_layer._2()._1(), tile_layer._2()._2())
        ser = geopysc.create_tuple_serializer(schema, value_type=TILE)
        returned_rdd = geopysc.create_python_rdd(rdd, ser)

        return (tile_layer._1(), returned_rdd, json.loads(tile_layer._3()))

    return [_formatter(tile_layer) for tile_layer in result]


def focal(geopysc,
          rdd_type,
          keyed_rdd,
          metadata,
          op,
          neighborhood,
          param1=0.0, param2=0.0, param3=0.0):

    """Performs the given focal operation on the layer contained in the RDD.

    The returned RDD is the result of applying the given focal
    operation to the input RDD.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        keyed_rdd (RDD): A RDD that contains tuples of dictionaries, (key, tile).
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
        metadata (dict): The metadata for this tile layer. This provides
            the information needed to resample the old tiles and create new ones.

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
        op (int): The focal operation to apply (e.g. SUM, ASPECT, SLOPE).
        neighborhood (str): The type of neighborhood to use (e.g. ANNULUS, SQUARE).
        param1 (float): For SLOPE this is the zFactor, otherwise it is the first argument to the neighborhood.
        param2 (float): The second argument to the neighborhood.
        param3 (float): The third argument to the neighborhood.

    Returns:
        tuple: A tuple containing (rdd, metadata).
            rdd (RDD): A layer containing the result of the focal operation.

                key (dict): The index of the tile within the layer. There are two different
                    types of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys deal with data that
                    have just a spatial component, whereas SpaceTimeKeys are for data with both a
                    spatial and time component.

                    Both SpatialKeys and SpaceTimeKeys share these fields:
                        col (int): The column number of the grid, runs east to west.
                        row (int): The row number of the grid, runs north to south.

                    SpaceTimeKeys also have an additional field:
                        instant (int): The time stamp of the tile.
                tile (dict): The data of the tile.

                    The fields to represent the tile:
                        data (np.ndarray): The tile data itself is represented as a 3D, numpy
                            array.  Note, even if the data was originally singleband, it will
                            be reformatted as a multiband tile and read and saved as such.
                        no_data_value (optional): The no data value of the tile. Can be a range of
                            types including None.
            metadata (dict): The metadata for the RDD.
                dict: The dictionary representation of the RDD's metadata.
                    The fields that are used to represent the metadata:
                        cellType (str): The value type of every cell within the rasters.
                        layoutDefinition (dict): Defines the raster layout of the rasters.

                        The fields that are used to represent the layoutDefinition:
                            extent (dict): The area covered by the layout tiles.
                            tileLayout (dict): The tile layout of the rasters.
                        extent (dict): The extent that covers the tiles.
                        crs (str): The CRS that the rasters are projected in.
                        bounds (dict): Represents the positions of the tile layer's tiles within
                            a gird.  These positions are represented by keys. There are two
                            different types of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys are
                            for data that only have a spatial component while SpaceTimeKeys are for
                            data with both spatial and temporal components.

                            Both SpatialKeys and SpaceTimeKeys share these fields:
                                The fields that are used to represent the bounds:
                                    minKey (dict): Represents where the tile layer begins in the
                                        gird.
                                    maxKey (dict): Represents where the tile layer ends in the gird.

                                    The fields that are used to represent the minKey and maxKey:
                                        col (int): The column number of the grid, runs east to west.
                                        row (int): The row number of the grid, runs north to south.

                            SpaceTimeKeys also have an additional field:
                                instant (int): The time stamp of the tile.

    """

    focal_wrapper = geopysc.rdd_focal
    key_type = geopysc.map_key_input(rdd_type, True)

    (java_rdd, schema1) = _convert_to_java_rdd(geopysc, key_type, keyed_rdd)

    result = focal_wrapper.focal(key_type,
                                 java_rdd,
                                 schema1,
                                 json.dumps(metadata),
                                 op,
                                 neighborhood,
                                 param1, param2, param3)

    rdd = result._1()
    schema2 = result._2()
    ser = geopysc.create_tuple_serializer(schema2, value_type=TILE)
    returned_rdd = geopysc.create_python_rdd(rdd, ser)

    return returned_rdd

def costdistance(geopysc,
                 rdd_type,
                 keyed_rdd,
                 metadata,
                 geometries,
                 max_distance):

    """Perform cost distance with the given (friction) layer and the given input geometries.

    The returned RDD contains the cost-distance layer RDD.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        keyed_rdd (RDD): A RDD that contains tuples of dictionaries, (key, tile).
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
        metadata (dict): The metadata for this tile layer. This provides
            the information needed to resample the old tiles and create new ones.

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
        geometries (list): A list of shapely geometries to use as starting points (must be in the same CRS as the friction layer).
        max_distance (float): The maximum cost that a path may reach before pruning.

    Returns:
        tuple: A tuple containing (rdd, metadata).
            rdd (RDD): A layer containing the result of the focal operation.

                key (dict): The index of the tile within the layer. There are two different
                    types of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys deal with data that
                    have just a spatial component, whereas SpaceTimeKeys are for data with both a
                    spatial and time component.

                    Both SpatialKeys and SpaceTimeKeys share these fields:
                        col (int): The column number of the grid, runs east to west.
                        row (int): The row number of the grid, runs north to south.

                    SpaceTimeKeys also have an additional field:
                        instant (int): The time stamp of the tile.
                tile (dict): The data of the tile.

                    The fields to represent the tile:
                        data (np.ndarray): The tile data itself is represented as a 3D, numpy
                            array.  Note, even if the data was originally singleband, it will
                            be reformatted as a multiband tile and read and saved as such.
                        no_data_value (optional): The no data value of the tile. Can be a range of
                            types including None.
            metadata (dict): The metadata for the RDD.
                dict: The dictionary representation of the RDD's metadata.
                    The fields that are used to represent the metadata:
                        cellType (str): The value type of every cell within the rasters.
                        layoutDefinition (dict): Defines the raster layout of the rasters.

                        The fields that are used to represent the layoutDefinition:
                            extent (dict): The area covered by the layout tiles.
                            tileLayout (dict): The tile layout of the rasters.
                        extent (dict): The extent that covers the tiles.
                        crs (str): The CRS that the rasters are projected in.
                        bounds (dict): Represents the positions of the tile layer's tiles within
                            a gird.  These positions are represented by keys. There are two
                            different types of keys, SpatialKeys and SpaceTimeKeys. SpatialKeys are
                            for data that only have a spatial component while SpaceTimeKeys are for
                            data with both spatial and temporal components.

                            Both SpatialKeys and SpaceTimeKeys share these fields:
                                The fields that are used to represent the bounds:
                                    minKey (dict): Represents where the tile layer begins in the
                                        gird.
                                    maxKey (dict): Represents where the tile layer ends in the gird.

                                    The fields that are used to represent the minKey and maxKey:
                                        col (int): The column number of the grid, runs east to west.
                                        row (int): The row number of the grid, runs north to south.

                            SpaceTimeKeys also have an additional field:
                                instant (int): The time stamp of the tile.

    """

    costdistance_wrapper = geopysc.rdd_costdistance
    key_type = geopysc.map_key_input(rdd_type, True)

    (java_rdd, schema1) = _convert_to_java_rdd(geopysc, key_type, keyed_rdd)

    wkts = [shapely.wkt.dumps(g) for g in geometries]

    result = costdistance_wrapper.costdistance(key_type,
                                               java_rdd,
                                               schema1,
                                               json.dumps(metadata),
                                               wkts, max_distance,
                                               geopysc.pysc._jsc.sc())

    rdd = result._1()
    schema2 = result._2()
    ser = geopysc.create_tuple_serializer(schema2, value_type=TILE)
    returned_rdd = geopysc.create_python_rdd(rdd, ser)

    return returned_rdd

def stitch(geopysc,
           rdd_type,
           keyed_rdd,
           metadata):

    """ Stitch the tiles contained in the RDD into one tile.

    Returns a tile.

    Args:
        geopysc (GeoPyContext): The GeoPyContext being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: SPATIAL and SPACETIME. Note: All of the
            GeoTiffs must have the same spatial type.
        keyed_rdd (RDD): A RDD that contains tuples of dictionaries, (key, tile).
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
        metadata (dict): The metadata for this tile layer. This provides
            the information needed to resample the old tiles and create new ones.

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

    Returns:
        tile (dict): The data of the tile.

            The fields to represent the tile:
                data (np.ndarray): The tile data itself is represented as a 3D, numpy
                    array.  Note, even if the data was originally singleband, it will
                    be reformatted as a multiband tile and read and saved as such.
                no_data_value (optional): The no data value of the tile. Can be a range of
                    types including None.
    """

    stitch_wrapper = geopysc.rdd_stitch
    key_type = geopysc.map_key_input(rdd_type, True)
    assert(key_type == 'SpatialKey')

    (java_rdd, schema1) = _convert_to_java_rdd(geopysc, key_type, keyed_rdd)

    result = stitch_wrapper.stitch(java_rdd,
                                   schema1,
                                   json.dumps(metadata))

    tile = result._1()
    schema2 = result._2()
    ser = geopysc.create_value_serializer(schema2, TILE)

    return ser.loads(tile)
