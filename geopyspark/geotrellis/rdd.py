'''
This module contains the ``RasterRDD`` and the ``TiledRasterRDD`` classes. Both of these classes are
wrappers of their Scala counterparts. These will be used in leau of actual PySpark RDDs
when performing operations.
'''
import json
import shapely.wkt
from geopyspark.geopyspark_utils import check_environment
check_environment()

from pyspark.storagelevel import StorageLevel
from shapely.geometry import Polygon, MultiPolygon
from shapely.wkt import dumps
from geopyspark.geotrellis import Metadata
from geopyspark.geotrellis.constants import (RESAMPLE_METHODS,
                                             OPERATIONS,
                                             SLOPE,
                                             ASPECT,
                                             SQUARE,
                                             NEIGHBORHOODS,
                                             NEARESTNEIGHBOR,
                                             FLOAT,
                                             TILE,
                                             SPATIAL,
                                             LESSTHANOREQUALTO,
                                             NODATAINT,
                                             CELL_TYPES
                                            )
from geopyspark.geotrellis.neighborhoods import Neighborhood


def _reclassify(srdd, value_map, data_type, boundary_strategy, replace_nodata_with):
    new_dict = {}

    for key, value in value_map.items():
        if not isinstance(key, data_type):
            val = value_map[key]
            for k in key:
                new_dict[k] = val
        else:
            new_dict[key] = value

    if data_type is int:
        if not replace_nodata_with:
            return srdd.reclassify(new_dict, boundary_strategy, NODATAINT)
        else:
            return srdd.reclassify(new_dict, boundary_strategy, replace_nodata_with)
    else:
        if not replace_nodata_with:
            return srdd.reclassifyDouble(new_dict, boundary_strategy, float('nan'))
        else:
            return srdd.reclassifyDouble(new_dict, boundary_strategy, replace_nodata_with)


class CachableRDD(object):
    """
    Base class for class that wraps a Scala RDD instance through a py4j reference.

    Attributes:
        geopysc (:class:`~geopyspark.GeoPyContext`): The ``GeoPyContext`` being used this session.
        srdd (py4j.java_gateway.JavaObject): The coresponding Scala RDD class.
    """

    def __init__(self):
        self.is_cached = False

    def wrapped_rdds(self):
        """
        Returns the list of RDD-containing objects wrapped by this object.
        The default implementation assumes that subclass contains a single
        RDD container, srdd, which implements the persist() and unpersist()
        methods.
        """
        return [self.srdd]

    def cache(self):
        """
        Persist this RDD with the default storage level (C{MEMORY_ONLY}).
        """
        self.persist()
        return self

    def persist(self, storageLevel=StorageLevel.MEMORY_ONLY):
        """
        Set this RDD's storage level to persist its values across operations
        after the first time it is computed. This can only be used to assign
        a new storage level if the RDD does not have a storage level set yet.
        If no storage level is specified defaults to (C{MEMORY_ONLY}).
        """

        javaStorageLevel = self.geopysc.pysc._getJavaStorageLevel(storageLevel)
        self.is_cached = True
        for srdd in self.wrapped_rdds():
            srdd.persist(javaStorageLevel)
        return self

    def unpersist(self):
        """
        Mark the RDD as non-persistent, and remove all blocks for it from
        memory and disk.
        """

        self.is_cached = False
        for srdd in self.wrapped_rdds():
            srdd.unpersist()
        return self

    def getNumPartitions(self):
        """Returns the number of partitions set for the wrapped RDD.

        Returns:
            Int: The number of partitions.
        """

        return self.srdd.rdd().getNumPartitions()

    def count(self):
        """Returns how many elements are within the wrapped RDD.

        Returns:
            Int: The number of elements in the RDD.
        """

        return self.rdd.rdd().count()


class RasterRDD(CachableRDD):
    """A wrapper of a RDD that contains GeoTrellis rasters.

    Represents a RDD that contains ``(K, V)``. Where ``K`` is either
    :cls:`~geopyspark.geotrellis.ProjectedExtent` or
    :cls:`~geopyspark.geotrellis.TemporalProjectedExtent` depending on the ``rdd_type`` of the RDD,
    and ``V`` being a :ref:`raster`.

    The data held within the RDD has not been tiled. Meaning the data has yet to be
    modified to fit a certain layout. See :ref:`raster_rdd` for more information.

    Args:
        geopysc (:class:`~geopyspark.GeoPyContext`): The ``GeoPyContext`` being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: ``SPATIAL`` and ``SPACETIME``.
        srdd (py4j.java_gateway.JavaObject): The coresponding Scala class. This is what allows
            ``RasterRDD`` to access the various Scala methods.

    Attributes:
        geopysc (:class:`~geopyspark.GeoPyContext`): The ``GeoPyContext`` being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is
            represented by the constants: ``SPATIAL`` and ``SPACETIME``.
        srdd (py4j.java_gateway.JavaObject): The coresponding Scala class. This is what allows
            ``RasterRDD`` to access the various Scala methods.
    """

    __slots__ = ['geopysc', 'rdd_type', 'srdd']

    def __init__(self, geopysc, rdd_type, srdd):
        CachableRDD.__init__(self)
        self.geopysc = geopysc
        self.rdd_type = rdd_type
        self.srdd = srdd

    @classmethod
    def from_numpy_rdd(cls, geopysc, rdd_type, numpy_rdd):
        """Create a ``RasterRDD`` from a numpy RDD.

        Args:
            geopysc (:class:`~geopyspark.GeoPyContext`): The ``GeoPyContext`` being used this
                session.
            rdd_type (str): What the spatial type of the geotiffs are. This is
                represented by the constants: ``SPATIAL`` and ``SPACETIME``.
            numpy_rdd (pyspark.RDD): A PySpark RDD that contains tuples of either
                :ref:`projected_extent`\s or :ref:`temporal_extent`\s and rasters that are represented
                by a numpy array.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterRDD`
        """

        key = geopysc.map_key_input(rdd_type, False)

        schema = geopysc.create_schema(key)
        ser = geopysc.create_tuple_serializer(schema, key_type=key, value_type=TILE)
        reserialized_rdd = numpy_rdd._reserialize(ser)

        if rdd_type == SPATIAL:
            srdd = \
                    geopysc._jvm.geopyspark.geotrellis.ProjectedRasterRDD.fromAvroEncodedRDD(
                        reserialized_rdd._jrdd, schema)
        else:
            srdd = \
                    geopysc._jvm.geopyspark.geotrellis.TemporalRasterRDD.fromAvroEncodedRDD(
                        reserialized_rdd._jrdd, schema)

        return cls(geopysc, rdd_type, srdd)

    def to_numpy_rdd(self):
        """Converts a ``RasterRDD`` to a numpy RDD.

        Note:
            Depending on the size of the data stored within the RDD, this can be an exspensive
            operation and should be used with caution.

        Returns:
            ``pyspark.RDD``
        """

        result = self.srdd.toAvroRDD()
        key = self.geopysc.map_key_input(self.rdd_type, False)
        ser = self.geopysc.create_tuple_serializer(result._2(), key_type=key,
                                                   value_type=TILE)
        return self.geopysc.create_python_rdd(result._1(), ser)

    def to_tiled_layer(self, extent=None, layout=None, crs=None, tile_size=256,
                       resample_method=NEARESTNEIGHBOR):
        """Converts this ``RasterRDD`` to a ``TiledRasterRDD``.

        This method combines :meth:`~geopyspark.geotrellis.rdd.RasterRDD.collect_metadata` and
        :meth:`~geopyspark.geotrellis.rdd.RasterRDD.tile_to_layout` into one step.

        Args:
            extent (:class:`~geopyspark.geotrellis.Extent`, optional): Specify layout extent,
                must also specify layout.
            layout (:obj:`~geopyspark.geotrellis.TileLayout`, optional): Specify tile layout, must
                also specify ``extent``.
            crs (str or int, optional): Ignore CRS from records and use given one instead.
            tile_size (int, optional): Pixel dimensions of each tile, if not using layout.
            resample_method (str, optional): The resample method to use for the reprojection.
                This is represented by the following constants: ``NEARESTNEIGHBOR``, ``BILINEAR``,
                ``CUBICCONVOLUTION``, ``LANCZOS``, ``AVERAGE``, ``MODE``, ``MEDIAN``, ``MAX``, and
                ``MIN``. If none is specified, then ``NEARESTNEIGHBOR`` is used.

        Note:
            ``extent`` and ``layout`` must both be defined if they are to be used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """

        return self.tile_to_layout(self.collect_metadata(extent, layout, crs, tile_size),
                                   resample_method)

    def convert_data_type(self, new_type):
        """Converts the underlying, raster values to a new ``CellType``.

        Args:
            new_type (str): The string representation of the ``CellType`` to convert to. It is
                represented by a constant such as ``INT16``, ``FLOAT64UD``, etc.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterRDD`

        Raises:
            ValueError: When an unsupported cell type is entered.
        """

        if new_type not in CELL_TYPES:
            raise ValueError(new_type, "Is not a know Cell Type")

        return RasterRDD(self.geopysc, self.rdd_type, self.srdd.convertDataType(new_type))

    def collect_metadata(self, extent=None, layout=None, crs=None, tile_size=256):
        """Iterate over RDD records and generates layer metadata desribing the contained
        rasters.

        Args:
            extent (:class:`~geopyspark.geotrellis.Extent`, optional): Specify layout extent, must
                also specify ``layout``.
            layout (:obj:`~geopyspark.geotrellis.TileLayout`, optional): Specify tile layout, must
                also specify ``extent``.
            crs (str or int, optional): Ignore CRS from records and use given one instead.
            tile_size (int, optional): Pixel dimensions of each tile, if not using ``layout``.

        Note:
            ``extent`` and ``layout`` must both be defined if they are to be used.

        Returns:
            :class:`~geopyspark.geotrellis.Metadata`

        Raises:
            TypeError: If either ``extent`` and ``layout`` is not defined but the other is.
        """

        if extent and not isinstance(extent, dict):
            extent = extent._asdict()

        if layout and not isinstance(layout, dict):
            layout = layout._asdict()

        if not crs:
            crs = ""

        if isinstance(crs, int):
            crs = str(crs)

        if extent and layout:
            json_metadata = self.srdd.collectMetadata(extent, layout, crs)
        elif not extent and not layout:
            json_metadata = self.srdd.collectMetadata(str(tile_size), crs)
        else:
            raise TypeError("Could not collect metadata with {} and {}".format(extent, layout))

        return Metadata.from_dict(json.loads(json_metadata))

    def reproject(self, target_crs, resample_method=NEARESTNEIGHBOR):
        """Reproject every individual raster to ``target_crs``, does not sample past tile boundary

        Args:
            target_crs (str or int): The CRS to reproject to. Can either be the EPSG code,
                well-known name, or a PROJ.4 projection string.
            resample_method (str, optional): The resample method to use for the reprojection.
                This is represented by the following constants: ``NEARESTNEIGHBOR``, ``BILINEAR``,
                ``CUBICCONVOLUTION``, ``LANCZOS``, ``AVERAGE``, ``MODE``, ``MEDIAN``, ``MAX``, and
                ``MIN``. If none is specified, then ``NEARESTNEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterRDD`
        """

        if resample_method not in RESAMPLE_METHODS:
            raise ValueError(resample_method, " Is not a known resample method.")

        if isinstance(target_crs, int):
            target_crs = str(target_crs)

        return RasterRDD(self.geopysc, self.rdd_type,
                         self.srdd.reproject(target_crs, resample_method))

    def cut_tiles(self, layer_metadata, resample_method=NEARESTNEIGHBOR):
        """Cut tiles to layout. May result in duplicate keys.

        Args:
            layer_metadata (:class:`~geopyspark.geotrellis.Metadata`): The
                ``Metadata`` of the ``RasterRDD`` instance.
            resample_method (str, optional): The resample method to use for the reprojection.
                This is represented by the following constants: ``NEARESTNEIGHBOR``, ``BILINEAR``,
                ``CUBICCONVOLUTION``, ``LANCZOS``, ``AVERAGE``, ``MODE``, ``MEDIAN``, ``MAX``, and
                ``MIN``. If none is specified, then ``NEARESTNEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """

        if resample_method not in RESAMPLE_METHODS:
            raise ValueError(resample_method, " Is not a known resample method.")

        if isinstance(layer_metadata, Metadata):
            layer_metadata = layer_metadata.to_dict()

        srdd = self.srdd.cutTiles(json.dumps(layer_metadata), resample_method)
        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def tile_to_layout(self, layer_metadata, resample_method=NEARESTNEIGHBOR):
        """Cut tiles to layout and merge overlapping tiles. This will produce unique keys.

        Args:
            layer_metadata (:class:`~geopyspark.geotrellis.Metadata`): The
                ``Metadata`` of the ``RasterRDD`` instance.
            resample_method (str, optional): The resample method to use for the reprojection.
                This is represented by the following constants: ``NEARESTNEIGHBOR``, ``BILINEAR``,
                ``CUBICCONVOLUTION``, ``LANCZOS``, ``AVERAGE``, ``MODE``, ``MEDIAN``, ``MAX``, and
                ``MIN``. If none is specified, then ``NEARESTNEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """

        if resample_method not in RESAMPLE_METHODS:
            raise ValueError(resample_method, " Is not a known resample method.")

        if isinstance(layer_metadata, Metadata):
            layer_metadata = layer_metadata.to_dict()

        srdd = self.srdd.tileToLayout(json.dumps(layer_metadata), resample_method)
        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def reclassify(self, value_map, data_type, boundary_strategy=LESSTHANOREQUALTO,
                   replace_nodata_with=None):
        """Changes the cell values of a raster based on how the data is broken up.

        Args:
            value_map (dict): A ``dict`` whose keys represent values where a break should occur and
                its values are the new value the cells within the break should become.
            data_type (type): The type of the values within the rasters. Can either be ``int`` or
                ``float``.
            boundary_strategy (str, optional): How the cells should be classified along the breaks.
                This is represented by the following constants: ``GREATERTHAN``,
                ``GREATERTHANOREQUALTO``, ``LESSTHAN``, ``LESSTHANOREQUALTO``, and ``EXACT``. If
                unspecified, then ``LESSTHANOREQUALTO`` will be used.
            replace_nodata_with (data_type, optional): When remapping values, nodata values must be
                treated separately.  If nodata values are intended to be replaced during the
                reclassify, this variable should be set to the intended value.  If unspecified,
                nodata values will be preserved.

        NOTE:
            NoData symbolizes a different value depending on if ``data_type`` is ``int`` or
            ``float``. For ``int``, the constant ``NODATAINT`` can be used which represents the
            NoData value for ``int`` in GeoTrellis. For ``float``, ``float('nan')`` is used to
            represent NoData.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterRDD`
        """

        srdd = _reclassify(self.srdd, value_map, data_type, boundary_strategy, replace_nodata_with)

        return RasterRDD(self.geopysc, self.rdd_type, srdd)

    def get_min_max(self):
        """Returns the maximum and minimum values of all of the rasters in the RDD.

        Returns:
            (float, float)
        """
        min_max = self.srdd.getMinMax()
        return (min_max._1(), min_max._2())

class TiledRasterRDD(CachableRDD):
    """Wraps a RDD of tiled, GeoTrellis rasters.

    Represents a RDD that contains ``(K, V)``. Where ``K`` is either
    :cls:`~geopyspark.geotrellis.SpatialKey` or :cls:`~geopyspark.geotrellis.SpaceTimeKey`
    depending on the ``rdd_type`` of the RDD, and ``V`` being a :ref:`raster`.

    The data held within the RDD is tiled. This means that the rasters have been modified to fit
    a larger layout. For more information, see :ref:`tiled-raster-rdd`.

    Args:
        geopysc (:class:`~geopyspark.GeoPyContext`): The ``GeoPyContext`` being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is represented by the
            constants: ``SPATIAL`` and ``SPACETIME``.
        srdd (py4j.java_gateway.JavaObject): The coresponding Scala class. This is what allows
            ``TiledRasterRDD`` to access the various Scala methods.

    Attributes:
        geopysc (:class:`~geopyspark.GeoPyContext`): The ``GeoPyContext`` being used this session.
        rdd_type (str): What the spatial type of the geotiffs are. This is represented by the
            constants: ``SPATIAL` and ``SPACETIME``.
        srdd (py4j.java_gateway.JavaObject): The coresponding Scala class. This is what allows
            ``RasterRDD`` to access the various Scala methods.
    """

    __slots__ = ['geopysc', 'rdd_type', 'srdd']

    def __init__(self, geopysc, rdd_type, srdd):
        CachableRDD.__init__(self)
        self.geopysc = geopysc
        self.rdd_type = rdd_type
        self.srdd = srdd

    @property
    def layer_metadata(self):
        """Layer metadata associated with this layer."""
        return Metadata.from_dict(json.loads(self.srdd.layerMetadata()))

    @property
    def zoom_level(self):
        """The zoom level of the RDD. Can be ``None``."""
        return self.srdd.getZoom()

    @classmethod
    def from_numpy_rdd(cls, geopysc, rdd_type, numpy_rdd, metadata):
        """Create a ``TiledRasterRDD`` from a numpy RDD.

        Args:
            geopysc (:class:`~geopyspark.GeoPyContext`): The ``GeoPyContext`` being used this
                session.
            rdd_type (str): What the spatial type of the geotiffs are. This is represented by the
                constants: ``SPATIAL`` and ``SPACETIME``.
            numpy_rdd (pyspark.RDD): A PySpark RDD that contains tuples of either
                :ref:`spatial-key` or :ref:`space-time-key` and rasters that are represented by a
                numpy array.
            metadata (:class:`~geopyspark.geotrellis.Metadata`): The ``Metadata`` of
                the ``TiledRasterRDD`` instance.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """
        key = geopysc.map_key_input(rdd_type, True)

        schema = geopysc.create_schema(key)
        ser = geopysc.create_tuple_serializer(schema, key_type=key, value_type=TILE)
        reserialized_rdd = numpy_rdd._reserialize(ser)

        if isinstance(metadata, Metadata):
            metadata = metadata.to_dict()

        if rdd_type == SPATIAL:
            srdd = \
                    geopysc._jvm.geopyspark.geotrellis.SpatialTiledRasterRDD.fromAvroEncodedRDD(
                        reserialized_rdd._jrdd, schema, json.dumps(metadata))
        else:
            srdd = \
                    geopysc._jvm.geopyspark.geotrellis.TemporalTiledRasterRDD.fromAvroEncodedRDD(
                        reserialized_rdd._jrdd, schema, json.dumps(metadata))

        return cls(geopysc, rdd_type, srdd)

    @classmethod
    def rasterize(cls, geopysc, rdd_type, geometry, extent, crs, cols, rows,
                  fill_value, instant=None):
        """Creates a ``TiledRasterRDD`` from a shapely geomety.

        Args:
            geopysc (:class:`~geopyspark.GeoPyContext`): The ``GeoPyContext`` being used this session.
            rdd_type (str): What the spatial type of the geotiffs are. This is
                represented by the constants: ``SPATIAL`` and ``SPACETIME``.
            geometry (str or shapely.geometry.Polygon): The value to be turned into a raster. Can
                either be a string or a ``Polygon``. If the value is a string, it must be the WKT
                string, geometry format.
            extent (:class:`~geopyspark.geotrellis.Extent`): The ``extent`` of the new raster.
            crs (str or int): The CRS the new raster should be in.
            cols (int): The number of cols the new raster should have.
            rows (int): The number of rows the new raster should have.
            fill_value (int): The value to fill the raster with.

                Note:
                    Only the area the raster intersects with the ``extent`` will have this value.
                    Any other area will be filled with GeoTrellis' NoData value for ``int`` which
                    is represented in GeoPySpark as the constant, ``NODATAINT``.
            instant(int, optional): Optional if the data has no time component (ie is ``SPATIAL``).
                Otherwise, it is requires and represents the time stamp of the data.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`

        Raises:
            TypeError: If ``geometry`` is not a ``str`` or a Polygon; or if there was a
                mistach in inputs like setting the ``rdd_type`` as ``SPATIAL`` but also setting
                ``instant``.
        """

        if not isinstance(geometry, str):
            try:
                geometry = dumps(geometry)
            except:
                raise TypeError(geometry, "Needs to be either a Shapely Geometry or a string")

        if not isinstance(extent, dict):
            extent = extent._asdict()

        if isinstance(crs, int):
            crs = str(crs)

        if instant and rdd_type != SPATIAL:
            srdd = geopysc._jvm.geopyspark.geotrellis.TemporalTiledRasterRDD.rasterize(
                geopysc.sc, geometry, extent, crs, instant, cols, rows, fill_value)
        elif not instant and rdd_type == SPATIAL:
            srdd = geopysc._jvm.geopyspark.geotrellis.SpatialTiledRasterRDD.rasterize(
                geopysc.sc, geometry, extent, crs, cols, rows, fill_value)
        else:
            raise TypeError("Abiguous inputs. Given ", instant, " but rdd_type is SPATIAL")

        return cls(geopysc, rdd_type, srdd)

    @classmethod
    def euclidean_distance(cls, geopysc, geometry, source_crs, zoom, cellType='float64'):
        """Calculates the Euclidean distance of a Shapely geometry.

        Args:
            geopysc (:class:`~geopyspark.GeoPyContext`): The ``GeoPyContext`` being used this
                session.
            geometry (shapely.geometry): The input geometry to compute the Euclidean distance
                for.
            source_crs (str or int): The CRS of the input geometry.
            zoom (int): The zoom level of the output raster.

        Note:
            This function may run very slowly for polygonal inputs if they cover many cells of
            the output raster.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RDD`
        """
        if isinstance(source_crs, int):
            source_crs = str(source_crs)

        srdd = geopysc._jvm.geopyspark.geotrellis.SpatialTiledRasterRDD.euclideanDistance(geopysc.sc, dumps(geometry), source_crs, cellType, zoom)
        return cls(geopysc, SPATIAL, srdd)

    def to_numpy_rdd(self):
        """Converts a ``TiledRasterRDD`` to a numpy RDD.

        Note:
            Depending on the size of the data stored within the RDD, this can be an exspensive
            operation and should be used with caution.

        Returns:
            ``pyspark.RDD``
        """
        result = self.srdd.toAvroRDD()
        key = self.geopysc.map_key_input(self.rdd_type, True)
        ser = self.geopysc.create_tuple_serializer(result._2(), key_type=key,
                                                   value_type=TILE)
        return self.geopysc.create_python_rdd(result._1(), ser)

    def convert_data_type(self, new_type):
        """Converts the underlying, raster values to a new ``CellType``.

        Args:
            new_type (str): The string representation of the ``CellType`` to convert to. It is
                represented by a constant such as ``INT16``, ``FLOAT64UD``, etc.
        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """
        return TiledRasterRDD(self.geopysc, self.rdd_type, self.srdd.convertDataType(new_type))

    def reproject(self, target_crs, extent=None, layout=None, scheme=FLOAT, tile_size=256,
                  resolution_threshold=0.1, resample_method=NEARESTNEIGHBOR):
        """Reproject RDD as tiled raster layer, samples surrounding tiles.

        Args:
            target_crs (str or int): The CRS to reproject to. Can either be the EPSG code,
                well-known name, or a PROJ.4 projection string.
            extent (:class:`~geopyspark.geotrellis.Extent`, optional): Specify the layout
                extent, must also specify ``layout``.
            layout (:obj:`~geopyspark.geotrellis.TileLayout`, optional): Specify the tile layout,
                must also specify ``extent``.
            scheme (str, optional): Which LayoutScheme should be used. Represented by the
                constants: ``FLOAT`` and ``ZOOM``. If not specified, then ``FLOAT`` is used.
            tile_size (int, optional): Pixel dimensions of each tile, if not using layout.
            resolution_threshold (double, optional): The percent difference between a cell size
                and a zoom level along with the resolution difference between the zoom level and
                the next one that is tolerated to snap to the lower-resolution zoom.
            resample_method (str, optional): The resample method to use for the reprojection.
                This is represented by the following constants: ``NEARESTNEIGHBOR``, ``BILINEAR``,
                ``CUBICCONVOLUTION``, ``LANCZOS``, ``AVERAGE``, ``MODE``, ``MEDIAN``, ``MAX``, and
                ``MIN``. If none is specified, then ``NEARESTNEIGHBOR`` is used.

        Note:
            ``extent`` and ``layout`` must both be defined if they are to be used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`

        Raises:
            TypeError: If either ``extent`` or ``layout`` is defined but the other is not.
        """

        if resample_method not in RESAMPLE_METHODS:
            raise ValueError(resample_method, " Is not a known resample method.")

        if extent and not isinstance(extent, dict):
            extent = extent._asdict()

        if layout and not isinstance(layout, dict):
            layout = layout._asdict()

        if isinstance(target_crs, int):
            target_crs = str(target_crs)

        if extent and layout:
            srdd = self.srdd.reproject(extent, layout, target_crs, resample_method)
        elif not extent and not layout:
            srdd = self.srdd.reproject(scheme, tile_size, resolution_threshold,
                                       target_crs, resample_method)
        else:
            raise TypeError("Could not collect reproject RDD with {} and {}".format(extent, layout))

        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def repartition(self, num_partitions):
        return TiledRasterRDD(self.geopysc, self.rdd_type, self.srdd.repartition(num_partitions))

    def lookup(self, col, row):
        """Return the value(s) in the image of a particular ``SpatialKey`` (given by col and row).

        Args:
            col (int): The ``SpatialKey`` column.
            row (int): The ``SpatialKey`` row.

        Returns:
            A list of numpy arrays (the tiles)

        Raises:
            ValueError: If using lookup on a non ``SPATIAL`` ``TiledRasterRDD``.
            IndexError: If col and row are not within the ``TiledRasterRDD``\'s bounds.
        """
        if self.rdd_type != SPATIAL:
            raise ValueError("Only TiledRasterRDDs with a rdd_type of Spatial can use lookup()")
        bounds = self.layer_metadata.bounds
        min_col = bounds.minKey.col
        min_row = bounds.minKey.row
        max_col = bounds.maxKey.col
        max_row = bounds.maxKey.row

        if col < min_col or col > max_col:
            raise IndexError("column out of bounds")
        if row < min_row or row > max_row:
            raise IndexError("row out of bounds")

        tup = self.srdd.lookup(col, row)
        array_of_tiles = tup._1()
        schema = tup._2()
        ser = self.geopysc.create_value_serializer(schema, TILE)

        return [ser.loads(tile)[0] for tile in array_of_tiles]

    def tile_to_layout(self, layout, resample_method=NEARESTNEIGHBOR):
        """Cut tiles to a given layout and merge overlapping tiles. This will produce unique keys.

        Args:
            layout (:obj:`~geopyspark.geotrellis.TileLayout`): Specify the ``TileLayout`` to cut
                to.
            resample_method (str, optional): The resample method to use for the reprojection.
                This is represented by the following constants: ``NEARESTNEIGHBOR``, ``BILINEAR``,
                ``CUBICCONVOLUTION``, ``LANCZOS``, ``AVERAGE``, ``MODE``, ``MEDIAN``, ``MAX``, and
                ``MIN``. If none is specified, then ``NEARESTNEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """

        if resample_method not in RESAMPLE_METHODS:
            raise ValueError(resample_method, " Is not a known resample method.")

        if not isinstance(layout, dict):
            layout = layout._asdict()

        srdd = self.srdd.tileToLayout(layout, resample_method)

        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def pyramid(self, end_zoom, start_zoom=None, resample_method=NEARESTNEIGHBOR):
        """Creates a pyramid of GeoTrellis layers where each layer reprsents a given zoom.

        Args:
            end_zoom (int): The zoom level where pyramiding should end. Represents
                the level that is most zoomed out.
            start_zoom (int, Optional): The zoom level where pyramiding should begin. Represents
                the level that is most zoomed in. If None, then will use the zoom level from
                :meth:`~geopyspark.geotrellis.rdd.TiledRasterRDD.zoom_level`.
            resample_method (str, optional): The resample method to use for the reprojection.
                This is represented by the following constants: ``NEARESTNEIGHBOR``, ``BILINEAR``,
                ``CUBICCONVOLUTION``, ``LANCZOS``, ``AVERAGE``, ``MODE``, ``MEDIAN``, ``MAX``, and
                ``MIN``. If none is specified, then ``NEARESTNEIGHBOR`` is used.

        Returns:
            ``[TiledRasterRDDs]``.

        Raises:
            ValueError: If the given ``resample_method`` is not known.
            ValueError: If the col and row count is not a power of 2.
        """

        if resample_method not in RESAMPLE_METHODS:
            raise ValueError(resample_method, " Is not a known resample method.")

        num_cols = self.layer_metadata.tile_layout.tileCols
        num_rows = self.layer_metadata.tile_layout.tileRows

        if (num_cols & (num_cols - 1)) != 0 or (num_rows & (num_rows - 1)) != 0:
            raise ValueError("Tiles must have a col and row count that is a power of 2")

        if start_zoom:
            start_zoom = start_zoom
        elif self.zoom_level:
            start_zoom = self.zoom_level
        else:
            raise ValueError("No start_zoom given.")

        result = self.srdd.pyramid(start_zoom, end_zoom, resample_method)

        return [TiledRasterRDD(self.geopysc, self.rdd_type, srdd) for srdd in result]

    def focal(self, operation, neighborhood=None, param_1=None, param_2=None, param_3=None):
        """Performs the given focal operation on the layers contained in the RDD.

        Args:
            operation (str): The focal operation. Represented by constants: ``SUM``, ``MIN``,
                ``MAX``, ``MEAN``, ``MEDIAN``, ``MODE``, ``STANDARDDEVIATION``, ``ASPECT``, and
                ``SLOPE``.
            neighborhood (str or :class:`~geopyspark.geotrellis.neighborhoods.Neighborhood`, optional):
                The type of neighborhood to use in the focal operation. This can be represented by
                either an instance of ``Neighborhood``, or by the constants: ``ANNULUS``, ``NEWS``,
                ``SQUARE``, ``WEDGE``, and ``CIRCLE``. Defaults to ``None``.
            param_1 (int or float, optional): If using ``SLOPE``, then this is the zFactor, else it
                is the first argument of ``neighborhood``.
            param_2 (int or float, optional): The second argument of the ``neighborhood``.
            param_3 (int or float, optional): The third argument of the ``neighborhood``.

        Note:
            ``param`` only need to be set if ``neighborhood`` is not an instance of
            ``Neighborhood`` or if ``neighborhood`` is ``None``.

            Any ``param`` that is not set will default to 0.0.

            If ``neighborhood`` is ``None`` then ``operation`` **must** be either ``SLOPE`` or
            ``ASPECT``.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`

        Raises:
            ValueError: If ``operation`` is not a known operation.
            ValueError: If ``neighborhood`` is not a known neighborhood.
            ValueError: If ``neighborhood`` was not set, and ``operation`` is not ``SLOPE`` or
                ``ASPECT``.
        """

        if operation not in OPERATIONS:
            raise ValueError(operation, "Is not a known operation.")

        if isinstance(neighborhood, Neighborhood):
            srdd = self.srdd.focal(operation, neighborhood.name, neighborhood.param_1,
                                   neighborhood.param_2, neighborhood.param_3)

        elif isinstance(neighborhood, str):
            if neighborhood not in NEIGHBORHOODS:
                raise ValueError(neighborhood, "is not a known neighborhood.")

            if param_1 is None:
                param_1 = 0.0
            if param_2 is None:
                param_2 = 0.0
            if param_3 is None:
                param_3 = 0.0

            srdd = self.srdd.focal(operation, neighborhood, float(param_1), float(param_2),
                                   float(param_3))

        elif not neighborhood and operation == SLOPE or operation == ASPECT:
            srdd = self.srdd.focal(operation, SQUARE, 1.0, 0.0, 0.0)

        else:
            raise ValueError("neighborhood must be set or the operation must be SLOPE or ASPECT")

        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def stitch(self):
        """Stitch all of the rasters within the RDD into one raster.

        Note:
            This can only be used on ``SPATIAL`` ``TiledRasterRDDs``.

        Returns:
            :ref:`raster`
        """

        if self.rdd_type != SPATIAL:
            raise ValueError("Only TiledRasterRDDs with a rdd_type of Spatial can use stitch()")

        tup = self.srdd.stitch()
        ser = self.geopysc.create_value_serializer(tup._2(), TILE)
        return ser.loads(tup._1())[0]

    def save_stitched(self, path, crop_bounds=None, crop_dimensions=None):
        """Stitch all of the rasters within the RDD into one raster.

        Args:
            path: The path of the geotiff to save.
            crop_bounds: Optional bounds with which to crop the raster before saving.
            crop_dimensions: Optional cols and rows of the image to save

        Note:
            This can only be used on `SPATIAL` TiledRasterRDDs.

        Returns:
            None
        """

        if self.rdd_type != SPATIAL:
            raise ValueError("Only TiledRasterRDDs with a rdd_type of Spatial can use stitch()")

        if crop_bounds:
            if crop_dimensions:
                self.srdd.save_stitched(path, list(crop_bounds), list(crop_dimensions))
            else:
                self.srdd.save_stitched(path, list(crop_bounds))
        elif crop_dimensions:
            raise Exception("crop_dimensions requires crop_bounds")
        else:
            self.srdd.save_stitched(path)

        return None

    def mask(self, geometries):
        """Masks the ``TiledRasterRDD`` so that only values that intersect the geometries will
        be available.

        Args:
            geometries (list):
                A list of shapely geometries to use as masks.

                Note:
                    All geometries must be in the same CRS as the TileLayer.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """

        if not isinstance(geometries, list):
            geometries = [geometries]
        wkts = [shapely.wkt.dumps(g) for g in geometries]
        srdd = self.srdd.mask(wkts)

        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def cost_distance(self, geometries, max_distance):
        """Performs cost distance of a TileLayer.

        Args:
            geometries (list):
                A list of shapely geometries to be used as a starting point.

                Note:
                    All geometries must be in the same CRS as the TileLayer.
            max_distance (int, float): The maximum cost that a path may reach before the operation.
                stops. This value can be an ``int`` or ``float``.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """

        wkts = [shapely.wkt.dumps(g) for g in geometries]
        srdd = self.srdd.costDistance(self.geopysc.sc, wkts, float(max_distance))

        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def hillshade(self, band=0, azimuth=315.0, altitude=45.0, z_factor=1.0):
        """Computes Hillshade (shaded relief) from a raster.

        The resulting raster will be a shaded relief map (a hill shading) based
        on the sun altitude, azimuth, and the z factor. The z factor is a
        conversion factor from map units to elevation units.

        Returns a raster of ShortConstantNoDataCellType.

        For descriptions of parameters, please see Esri Desktop's
        `description <http://goo.gl/DtVDQ>`_ of Hillshade.

        Args:
            band (int) [default = 0]: The band of the raster to base the
                hillshade calculation on.
            azimuth (float) [default = 315]
            altitude (float) [default = 45]
            z_factor (float) [default = 1.0]
        """
        srdd = self.srdd.hillshade(self.geopysc.sc, azimuth, altitude, z_factor, band)

        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def reclassify(self, value_map, data_type, boundary_strategy=LESSTHANOREQUALTO,
                   replace_nodata_with=None):
        """Changes the cell values of a raster based on how the data is broken up.

        Args:
            value_map (dict): A ``dict`` whose keys represent values where a break should occur and
                its values are the new value the cells within the break should become.
            data_type (type): The type of the values within the rasters. Can either be ``int`` or
                ``float``.
            boundary_strategy (str, optional): How the cells should be classified along the breaks.
                This is represented by the following constants: ``GREATERTHAN``,
                ``GREATERTHANOREQUALTO``, ``LESSTHAN``, ``LESSTHANOREQUALTO``, and ``EXACT``. If
                unspecified, then ``LESSTHANOREQUALTO`` will be used.
            replace_nodata_with (data_type, optional): When remapping values, nodata values must be
                treated separately.  If nodata values are intended to be replaced during the
                reclassify, this variable should be set to the intended value.  If unspecified,
                nodata values will be preserved.

        NOTE:
            NoData symbolizes a different value depending on if ``data_type`` is ``int`` or
            ``float``. For ``int``, the constant ``NODATAINT`` can be used which represents the
            NoData value for ``int`` in GeoTrellis. For ``float``, ``float('nan')`` is used to
            represent NoData.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """

        srdd = _reclassify(self.srdd, value_map, data_type, boundary_strategy, replace_nodata_with)

        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def get_min_max(self):
        """Returns the maximum and minimum values of all of the rasters in the RDD.

        Returns:
            ``(float, float)``
        """
        min_max = self.srdd.getMinMax()
        return (min_max._1(), min_max._2())

    def normalize(self, old_min, old_max, new_min, new_max):
        """Finds the min value that is contained within the given geometry.

        Args:
            old_min (float): Old minimum.
            old_max (float): Old maximum.
            new_min (float): New minimum to normalize to.
            new_max (float): New maximum to normalize to.
        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`
        """
        srdd = self.srdd.normalize(old_min, old_max, new_min, new_max)

        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    @staticmethod
    def _process_polygonal_summary(geometry, operation):
        if isinstance(geometry, Polygon) or isinstance(geometry, MultiPolygon):
            geometry = dumps(geometry)
        if not isinstance(geometry, str):
            raise ValueError("geometry must be either a Polygon, MultiPolygon, or a String")

        return operation(geometry)

    def polygonal_min(self, geometry, data_type):
        """Finds the min value that is contained within the given geometry.

        Args:
            geometry (`shapely.geometry.Polygon` or `shapely.geometry.MultiPolygon` or str): A
                Shapely ``Polygon`` or ``MultiPolygon`` that represents the area where the summary
                should be computed; or a WKT string representation of the geometry.
            data_type (type): The type of the values within the rasters. Can either be ``int`` or
                ``float``.

        Returns:
            ``int`` or ``float`` depending on ``data_type``.

        Raises:
            TypeError: If ``data_type`` is not an ``int`` or ``float``.
        """

        if data_type is int:
            return self._process_polygonal_summary(geometry, self.srdd.polygonalMin)
        elif data_type is float:
            return self._process_polygonal_summary(geometry, self.srdd.polygonalMinDouble)
        else:
            raise TypeError("data_type must be either int or float.")

    def polygonal_max(self, geometry, data_type):
        """Finds the max value that is contained within the given geometry.

        Args:
            geometry (`shapely.geometry.Polygon` or `shapely.geometry.MultiPolygon` or str): A
                Shapely ``Polygon`` or ``MultiPolygon`` that represents the area where the summary
                should be computed; or a WKT string representation of the geometry.
            data_type (type): The type of the values within the rasters. Can either be ``int`` or
                ``float``.

        Returns:
            ``int`` or ``float`` depending on ``data_type``.

        Raises:
            TypeError: If ``data_type`` is not an ``int`` or ``float``.
        """

        if data_type is int:
            return self._process_polygonal_summary(geometry, self.srdd.polygonalMax)
        elif data_type is float:
            return self._process_polygonal_summary(geometry, self.srdd.polygonalMaxDouble)
        else:
            raise TypeError("data_type must be either int or float.")

    def polygonal_sum(self, geometry, data_type):
        """Finds the sum of all of the values that are contained within the given geometry.

        Args:
            geometry (`shapely.geometry.Polygon` or `shapely.geometry.MultiPolygon` or str): A
                Shapely ``Polygon`` or ``MultiPolygon`` that represents the area where the summary
                should be computed; or a WKT string representation of the geometry.
            data_type (type): The type of the values within the rasters. Can either be ``int`` or
                ``float``.

        Returns:
            ``int`` or ``float`` depending on ``data_type``.

        Raises:
            TypeError: If ``data_type`` is not an ``int`` or ``float``.
        """

        if data_type is int:
            return self._process_polygonal_summary(geometry, self.srdd.polygonalSum)
        elif data_type is float:
            return self._process_polygonal_summary(geometry, self.srdd.polygonalSumDouble)
        else:
            raise TypeError("data_type must be either int or float.")

    def polygonal_mean(self, geometry):
        """Finds the mean of all of the values that are contained within the given geometry.

        Args:
            geometry (`shapely.geometry.Polygon` or `shapely.geometry.MultiPolygon` or str): A
                Shapely ``Polygon`` or ``MultiPolygon`` that represents the area where the summary
                should be computed; or a WKT string representation of the geometry.

        Returns:
            ``float``
        """

        return self._process_polygonal_summary(geometry, self.srdd.polygonalMean)
    def get_quantile_breaks(self, num_breaks):
        """Returns quantile breaks for this RDD.

        Args:
            num_breaks (int): The number of breaks to return.

        Returns:
            ``[float]``
        """
        return list(self.srdd.quantileBreaks(num_breaks))

    def get_quantile_breaks_exact_int(self, num_breaks):
        """Returns quantile breaks for this RDD.
        This version uses the ``FastMapHistogram``, which counts exact integer values.
        If your RDD has too many values, this can cause memory errors.

        Args:
            num_breaks (int): The number of breaks to return.

        Returns:
            ``[int]``
        """
        return list(self.srdd.quantileBreaksExactInt(num_breaks))

    def is_floating_point_layer(self):
        """Determines whether the content of the TiledRasterRDD is of floating point type.

        Args:
            None

        Returns:
            [boolean]
        """
        return self.srdd.isFloatingPointLayer()

    def get_histogram(self):
        """Returns an array of Java histogram objects, one for each band of the raster.

        Args:
            None

        Returns:
            An array of Java objects containing the histograms of each band
        """
        if self.is_floating_point_layer:
            histogram = self.srdd.getDoubleHistograms()
        else:
            histogram = self.srdd.getIntHistograms()
        return histogram

    def _process_operation(self, value, operation):
        if isinstance(value, int) or isinstance(value, float):
            srdd = operation(value)
        elif isinstance(value, TiledRasterRDD):
            if self.rdd_type != value.rdd_type:
                raise ValueError("Both TiledRasterRDDs need to have the same rdd_type")

            if self.layer_metadata.tile_layout != value.layer_metadata.tile_layout:
                raise ValueError("Both TiledRasterRDDs need to have the same layout")

            srdd = operation(value.srdd)
        elif isinstance(value, list):
            srdd = operation(list(map(lambda x: x.srdd, value)))
        else:
            raise TypeError("Local operation cannot be performed with", value)

        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def __add__(self, value):
        return self._process_operation(value, self.srdd.localAdd)

    def __radd__(self, value):
        return self._process_operation(value, self.srdd.localAdd)

    def __sub__(self, value):
        return self._process_operation(value, self.srdd.localSubtract)

    def __rsub__(self, value):
        return self._process_operation(value, self.srdd.reverseLocalSubtract)

    def __mul__(self, value):
        return self._process_operation(value, self.srdd.localMultiply)

    def __rmul__(self, value):
        return self._process_operation(value, self.srdd.localMultiply)

    def __truediv__(self, value):
        return self._process_operation(value, self.srdd.localDivide)

    def __rtruediv__(self, value):
        return self._process_operation(value, self.srdd.reverseLocalDivide)
