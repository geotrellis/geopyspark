'''
This module contains the ``RasterLayer`` and the ``TiledRasterLayer`` classes. Both of these
classes are wrappers of their Scala counterparts. These will be used in leau of actual PySpark RDDs
when performing operations.
'''
import json
import shapely.wkb
from shapely.geometry import Polygon, MultiPolygon
from geopyspark.geotrellis.protobufcodecs import multibandtile_decoder
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer
from geopyspark.geopyspark_utils import ensure_pyspark
ensure_pyspark()

from pyspark.storagelevel import StorageLevel

from geopyspark import map_key_input, create_python_rdd
from geopyspark.geotrellis import Metadata, Tile, LocalLayout, GlobalLayout, LayoutDefinition
from geopyspark.geotrellis.histogram import Histogram
from geopyspark.geotrellis.constants import (Operation,
                                             Neighborhood as nb,
                                             ResampleMethod,
                                             ClassificationStrategy,
                                             CellType,
                                             LayoutScheme,
                                             LayerType,
                                             StorageMethod,
                                             ColorSpace,
                                             Compression,
                                             NO_DATA_INT
                                            )
from geopyspark.geotrellis.neighborhood import Neighborhood


__all__ = ["RasterLayer", "TiledRasterLayer", "Pyramid"]


def _reclassify(srdd, value_map, data_type, classification_strategy, replace_nodata_with):
    new_dict = {}

    for key, value in value_map.items():
        if isinstance(key, data_type):
            new_dict[key] = value
        elif isinstance(key, (list, tuple)):
            val = value_map[key]
            for k in key:
                new_dict[k] = val
        else:
            raise TypeError("Expected", data_type, "list, or tuple for the key, but the type was", type(key))

    if data_type is int:
        if not replace_nodata_with:
            return srdd.reclassify(new_dict, ClassificationStrategy(classification_strategy).value,
                                   NO_DATA_INT)
        else:
            return srdd.reclassify(new_dict, ClassificationStrategy(classification_strategy).value,
                                   replace_nodata_with)
    else:
        if not replace_nodata_with:
            return srdd.reclassifyDouble(new_dict, ClassificationStrategy(classification_strategy).value,
                                         float('nan'))
        else:
            return srdd.reclassifyDouble(new_dict, ClassificationStrategy(classification_strategy).value,
                                         replace_nodata_with)


def _to_geotiff_rdd(pysc, srdd, storage_method, rows_per_strip, tile_dimensions, compression,
                    color_space, color_map, head_tags, band_tags):
    storage_method = StorageMethod(storage_method).value
    compression = Compression(compression).value
    color_space = ColorSpace(color_space).value

    if storage_method == StorageMethod.STRIPED:
        if rows_per_strip:
            scala_storage = \
                    pysc._gateway.jvm.geotrellis.raster.io.geotiff.Striped.apply(rows_per_strip)
        else:
            scala_storage = \
                    pysc._gateway.jvm.geotrellis.raster.io.geotiff.Striped.apply()
    else:
        scala_storage = pysc._gateway.jvm.geotrellis.raster.io.geotiff.Tiled(*tile_dimensions)

    if color_map:
        return srdd.toGeoTiffRDD(scala_storage,
                                 compression,
                                 color_space,
                                 color_map.cmap,
                                 head_tags or {},
                                 band_tags or [])
    else:
        return srdd.toGeoTiffRDD(scala_storage,
                                 compression,
                                 color_space,
                                 head_tags or {},
                                 band_tags or [])


class CachableLayer(object):
    """
    Base class for class that wraps a Scala RDD instance through a py4j reference.

    Attributes:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
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

        javaStorageLevel = self.pysc._getJavaStorageLevel(storageLevel)
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

        return self.srdd.rdd().count()


class RasterLayer(CachableLayer):
    """A wrapper of a RDD that contains GeoTrellis rasters.

    Represents a layer that wraps a RDD that contains ``(K, V)``. Where ``K`` is either
    :class:`~geopyspark.geotrellis.ProjectedExtent` or
    :class:`~geopyspark.geotrellis.TemporalProjectedExtent` depending on the ``layer_type`` of the RDD,
    and ``V`` being a :ref:`raster`.

    The data held within this layer has not been tiled. Meaning the data has yet to be
    modified to fit a certain layout. See :ref:`raster_rdd` for more information.

    Args:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        layer_type (str or :class:`geopyspark.geotrellis.constants.LayerType`): What the spatial type
            of the geotiffs are. This is represented by either constants within ``LayerType`` or by
            a string.
        srdd (py4j.java_gateway.JavaObject): The coresponding Scala class. This is what allows
            ``RasterLayer`` to access the various Scala methods.

    Attributes:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        layer_type (str or :class:`geopyspark.geotrellis.constants.LayerType`): What the spatial type
            of the geotiffs are. This is represented by either constants within ``LayerType`` or by
            a string.
        srdd (py4j.java_gateway.JavaObject): The coresponding Scala class. This is what allows
            ``RasterLayer`` to access the various Scala methods.
    """

    __slots__ = ['pysc', 'layer_type', 'srdd']

    def __init__(self, pysc, layer_type, srdd):
        CachableLayer.__init__(self)
        self.pysc = pysc
        self.layer_type = layer_type
        self.srdd = srdd

    @classmethod
    def from_numpy_rdd(cls, pysc, layer_type, numpy_rdd):
        """Create a ``RasterLayer`` from a numpy RDD.

        Args:
            pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
            layer_type (str or :class:`geopyspark.geotrellis.constants.LayerType`): What the spatial type
                of the geotiffs are. This is represented by either constants within ``LayerType`` or by
                a string.
            numpy_rdd (pyspark.RDD): A PySpark RDD that contains tuples of either
                :class:`~geopyspark.geotrellis.ProjectedExtent`\s or
                :class:`~geopyspark.geotrellis.TemporalProjectedExtent`\s and rasters that
                are represented by a numpy array.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterLayer`
        """

        key = map_key_input(LayerType(layer_type).value, False)
        ser = ProtoBufSerializer.create_tuple_serializer(key_type=key)
        reserialized_rdd = numpy_rdd._reserialize(ser)

        if layer_type == LayerType.SPATIAL:
            srdd = \
                    pysc._gateway.jvm.geopyspark.geotrellis.ProjectedRasterRDD.fromProtoEncodedRDD(
                        reserialized_rdd._jrdd)
        else:
            srdd = \
                    pysc._gateway.jvm.geopyspark.geotrellis.TemporalRasterRDD.fromProtoEncodedRDD(
                        reserialized_rdd._jrdd)

        return cls(pysc, layer_type, srdd)

    def to_numpy_rdd(self):
        """Converts a ``RasterLayer`` to a numpy RDD.

        Note:
            Depending on the size of the data stored within the RDD, this can be an exspensive
            operation and should be used with caution.

        Returns:
            RDD
        """

        result = self.srdd.toProtoRDD()
        key = map_key_input(LayerType(self.layer_type).value, False)
        ser = ProtoBufSerializer.create_tuple_serializer(key_type=key)

        return create_python_rdd(self.pysc, result, ser)

    def to_png_rdd(self, color_map):
        """Converts the rasters within this layer to PNGs which are then converted to bytes.
        This is returned as a RDD[(K, bytes)].

        Args:
            color_map (:class:`~geopyspark.geotrellis.color.ColorMap`): A ``ColorMap`` instance
                used to color the PNGs.

        Returns:
            RDD[(K, bytes)]
        """

        result = self.srdd.toPngRDD(color_map.cmap)
        key = map_key_input(LayerType(self.layer_type).value, False)
        ser = ProtoBufSerializer.create_image_rdd_serializer(key_type=key)

        return create_python_rdd(self.pysc, result, ser)

    def to_geotiff_rdd(self,
                       storage_method=StorageMethod.STRIPED,
                       rows_per_strip=None,
                       tile_dimensions=(256, 256),
                       compression=Compression.NO_COMPRESSION,
                       color_space=ColorSpace.BLACK_IS_ZERO,
                       color_map=None,
                       head_tags=None,
                       band_tags=None):
        """Converts the rasters within this layer to GeoTiffs which are then converted to bytes.
        This is returned as a ``RDD[(K, bytes)]``. Where ``K`` is either ``ProjectedExtent`` or
        ``TemporalProjectedExtent``.

        Args:
            storage_method (str or :class:`~geopyspark.geotrellis.constants.StorageMethod`, optional): How
                the segments within the GeoTiffs should be arranged. Default is
                ``StorageMethod.STRIPED``.
            rows_per_strip (int, optional): How many rows should be in each strip segment of the
                GeoTiffs if ``storage_method`` is ``StorageMethod.STRIPED``. If ``None``, then the
                strip size will default to a value that is 8K or less.
            tile_dimensions ((int, int), optional): The length and width for each tile segment of the GeoTiff
                if ``storage_method`` is ``StorageMethod.TILED``. If ``None`` then the default size
                is ``(256, 256)``.
            compression (str or :class:`~geopyspark.geotrellis.constants.Compression`, optional): How the
                data should be compressed. Defaults to ``Compression.NO_COMPRESSION``.
            color_space (str or :class:`~geopyspark.geotrellis.constants.ColorSpace`, optional): How the
                colors should be organized in the GeoTiffs. Defaults to
                ``ColorSpace.BLACK_IS_ZERO``.
            color_map (:class:`~geopyspark.geotrellis.color.ColorMap`, optional): A ``ColorMap``
                instance used to color the GeoTiffs to a different gradient.
            head_tags (dict, optional): A ``dict`` where each key and value is a ``str``.
            band_tags (list, optional): A ``list`` of ``dict``\s where each key and value is a
                ``str``.

            Note:
                For more information on the contents of the tags, see www.gdal.org/gdal_datamodel.html

        Returns:
            RDD[(K, bytes)]
        """

        result = _to_geotiff_rdd(self.pysc, self.srdd, storage_method, rows_per_strip, tile_dimensions,
                                 compression, color_space, color_map, head_tags, band_tags)

        key = map_key_input(LayerType(self.layer_type).value, False)
        ser = ProtoBufSerializer.create_image_rdd_serializer(key_type=key)

        return create_python_rdd(self.pysc, result, ser)

    def to_tiled_layer(self, extent=None, layout=None, crs=None, tile_size=256,
                       resample_method=ResampleMethod.NEAREST_NEIGHBOR):
        """Converts this ``RasterLayer`` to a ``TiledRasterLayer``.

        This method combines :meth:`~geopyspark.geotrellis.rdd.RasterLayer.collect_metadata` and
        :meth:`~geopyspark.geotrellis.rdd.RasterLayer.tile_to_layout` into one step.

        Args:
            extent (:class:`~geopyspark.geotrellis.Extent`, optional): Specify layout extent,
                must also specify layout.
            layout (:obj:`~geopyspark.geotrellis.TileLayout`, optional): Specify tile layout, must
                also specify ``extent``.
            crs (str or int, optional): Ignore CRS from records and use given one instead.
            tile_size (int, optional): Pixel dimensions of each tile, if not using layout.
            resample_method (str or :class:`~geopyspark.geotrellis.constants.ResampleMethod`, optional):
                The resample method to use for the reprojection. If none is specified, then
                ``ResampleMethods.NEAREST_NEIGHBOR`` is used.

        Note:
            ``extent`` and ``layout`` must both be defined if they are to be used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterLayer`
        """

        return self.tile_to_layout(self.collect_metadata(extent, layout, crs, tile_size),
                                   resample_method)

    def bands(self, band):
        """Select a subsection of bands from the ``Tile``\s within the layer.

        Note:
            There could be potential high performance cost if operations are performed
            between two sub-bands of a large data set.

        Note:
            Due to the natue of GeoPySpark's backend, if selecting a band that is out of bounds
            then the error returned will be a ``py4j.protocol.Py4JJavaError`` and not a normal
            Python error.

        Args:
            band (int or tuple or list or range): The band(s) to be selected from the ``Tile``\s.
                Can either be a single ``int``, or a collection of ``int``\s.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterLayer` with the selected bands.
        """

        if isinstance(band, range):
            band = list(band)

        if isinstance(band, (int, tuple, list)):
            result = self.srdd.bands(band)
        else:
            raise TypeError("band must be an int, tuple, or list. Recieved", type(band), "instead.")

        return RasterLayer(self.pysc, self.layer_type, result)

    def map_tiles(self, func):
        """Maps over each ``Tile`` within the layer with a given function.

        Note:
            This operation first needs to deserialize the wrapped ``RDD`` into Python and then
            serialize the ``RDD`` back into a ``RasterRDD`` once the mapping is done. Thus,
            it is advised to chain together operations to reduce performance cost.

        Args:
            func (:class:`~geopyspark.geotrellis.Tile` => :class:`~geopyspark.geotrellis.Tile`): A
                function that takes a ``Tile`` and returns a ``Tile``.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterLayer`
        """

        python_rdd = self.to_numpy_rdd()

        return RasterLayer.from_numpy_rdd(self.pysc, self.layer_type,
                                          python_rdd.mapValues(lambda tile: func(tile.cells)))

    def map_cells(self, func):
        """Maps over the cells of each ``Tile`` within the layer with a given function.

        Note:
            This operation first needs to deserialize the wrapped ``RDD`` into Python and then
            serialize the ``RDD`` back into a ``TiledRasterRDD`` once the mapping is done. Thus,
            it is advised to chain together operations to reduce performance cost.

        Args:
            func (cells, nd => cells): A function that takes two arguements: ``cells`` and
                ``nd``. Where ``cells`` is the numpy array and ``nd`` is the ``no_data_value`` of
                the tile. It returns ``cells`` which are the new cells values of the tile
                represented as a numpy array.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterLayer`
        """

        python_rdd = self.to_numpy_rdd()

        def tile_func(cells, cell_type, no_data_value):
            return Tile(func(cells, no_data_value), cell_type, no_data_value)

        return RasterLayer.from_numpy_rdd(self.pysc, self.layer_type,
                                          python_rdd.mapValues(lambda tile: tile_func(*tile)))

    def convert_data_type(self, new_type, no_data_value=None):
        """Converts the underlying, raster values to a new ``CellType``.

        Args:
            new_type (str or :class:`~geopyspark.geotrellis.constants.CellType`): The data type the
                cells should be to converted to.
            no_data_value (int or float, optional): The value that should be marked as NoData.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterLayer`

        Raises:
            ValueError: If ``no_data_value`` is set and the ``new_type`` contains raw values.
            ValueError: If ``no_data_value`` is set and ``new_type`` is a boolean.
        """

        new_type = CellType(new_type).value

        if no_data_value:
            if 'bool' in new_type:
                raise ValueError("Cannot add user defined types to Bool")
            elif 'raw' in new_type:
                raise ValueError("Cannot add user defined types to raw values")

            no_data_constant = new_type + "ud" + str(no_data_value)

            return RasterLayer(self.pysc, self.layer_type,
                               self.srdd.convertDataType(no_data_constant))
        else:
            return RasterLayer(self.pysc, self.layer_type,
                               self.srdd.convertDataType(new_type))

    def collect_metadata(self, extent=None, layout=None, crs=None, tile_size=256):
        """Iterate over the RDD records and generates layer metadata desribing the contained
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

    def reproject(self, target_crs, resample_method=ResampleMethod.NEAREST_NEIGHBOR):
        """Reproject every individual raster to ``target_crs``, does not sample past tile boundary

        Args:
            target_crs (str or int): The CRS to reproject to. Can either be the EPSG code,
                well-known name, or a PROJ.4 projection string.
            resample_method (str or :class:`~geopyspark.geotrellis.constants.ResampleMethod`, optional):
                The resample method to use for the reprojection. If none is specified, then
                ``ResampleMethods.NEAREST_NEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterLayer`
        """

        if isinstance(target_crs, int):
            target_crs = str(target_crs)

        return RasterLayer(self.pysc, self.layer_type,
                           self.srdd.reproject(target_crs, ResampleMethod(resample_method)))

    def cut_tiles(self, layer_metadata, resample_method=ResampleMethod.NEAREST_NEIGHBOR):
        """Cut tiles to layout. May result in duplicate keys.

        Args:
            layer_metadata (:class:`~geopyspark.geotrellis.Metadata`): The
                ``Metadata`` of the ``RasterLayer`` instance.
            resample_method (str or :class:`~geopyspark.geotrellis.constants.ResampleMethod`, optional):
                The resample method to use for the reprojection. If none is specified, then
                ``ResampleMethods.NEAREST_NEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
        """

        if isinstance(layer_metadata, Metadata):
            layer_metadata = layer_metadata.to_dict()

        srdd = self.srdd.cutTiles(json.dumps(layer_metadata), ResampleMethod(resample_method))
        return TiledRasterLayer(self.pysc, self.layer_type, srdd)

    def tile_to_layout(self, layer_metadata, resample_method=ResampleMethod.NEAREST_NEIGHBOR):
        """Cut tiles to layout and merge overlapping tiles. This will produce unique keys.

        Args:
            layer_metadata (:class:`~geopyspark.geotrellis.Metadata`): The
                ``Metadata`` of the ``RasterLayer`` instance.
            resample_method (str or :class:`~geopyspark.geotrellis.constants.ResampleMethod`, optional):
                The resample method to use for the reprojection. If none is specified, then
                ``ResampleMethods.NEAREST_NEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
        """

        if isinstance(layer_metadata, Metadata):
            layer_metadata = layer_metadata.to_dict()

        srdd = self.srdd.tileToLayout(json.dumps(layer_metadata),
                                      ResampleMethod(resample_method))
        return TiledRasterLayer(self.pysc, self.layer_type, srdd)

    def reclassify(self, value_map, data_type,
                   classification_strategy=ClassificationStrategy.LESS_THAN_OR_EQUAL_TO,
                   replace_nodata_with=None):
        """Changes the cell values of a raster based on how the data is broken up.

        Args:
            value_map (dict): A ``dict`` whose keys represent values where a break should occur and
                its values are the new value the cells within the break should become.
            data_type (type): The type of the values within the rasters. Can either be ``int`` or
                ``float``.
            classification_strategy (str or :class:`~geopyspark.geotrellis.constants.ClassificationStrategy`, optional):
                How the cells should be classified along the breaks. If unspecified, then
                ``ClassificationStrategy.LESS_THAN_OR_EQUAL_TO`` will be used.
            replace_nodata_with (data_type, optional): When remapping values, nodata values must be
                treated separately.  If nodata values are intended to be replaced during the
                reclassify, this variable should be set to the intended value.  If unspecified,
                nodata values will be preserved.

        NOTE:
            NoData symbolizes a different value depending on if ``data_type`` is ``int`` or
            ``float``. For ``int``, the constant ``NO_DATA_INT`` can be used which represents the
            NoData value for ``int`` in GeoTrellis. For ``float``, ``float('nan')`` is used to
            represent NoData.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.RasterLayer`
        """

        srdd = _reclassify(self.srdd, value_map, data_type, classification_strategy, replace_nodata_with)

        return RasterLayer(self.pysc, self.layer_type, srdd)

    def get_min_max(self):
        """Returns the maximum and minimum values of all of the rasters in the layer.

        Returns:
            (float, float)
        """

        min_max = self.srdd.getMinMax()
        return (min_max._1(), min_max._2())

    def __str__(self):
        return "RasterLayer(layer_type={})".format(self.layer_type)

    def __repr__(self):
        return "RasterLayer(layer_type={})".format(self.layer_type)


class TiledRasterLayer(CachableLayer):
    """Wraps a RDD of tiled, GeoTrellis rasters.

    Represents a RDD that contains ``(K, V)``. Where ``K`` is either
    :class:`~geopyspark.geotrellis.SpatialKey` or :class:`~geopyspark.geotrellis.SpaceTimeKey`
    depending on the ``layer_type`` of the RDD, and ``V`` being a :ref:`raster`.

    The data held within the layer is tiled. This means that the rasters have been modified to fit
    a larger layout. For more information, see :ref:`tiled-raster-rdd`.

    Args:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        layer_type (str or :class:`geopyspark.geotrellis.constants.LayerType`): What the spatial type
            of the geotiffs are. This is represented by either constants within ``LayerType`` or by
            a string.
        srdd (py4j.java_gateway.JavaObject): The coresponding Scala class. This is what allows
            ``TiledRasterLayer`` to access the various Scala methods.

    Attributes:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        layer_type (str or :class:`geopyspark.geotrellis.constants.LayerType`): What the spatial type
            of the geotiffs are. This is represented by either constants within ``LayerType`` or by
            a string.
        srdd (py4j.java_gateway.JavaObject): The coresponding Scala class. This is what allows
            ``RasterLayer`` to access the various Scala methods.
        is_floating_point_layer (bool): Whether the data within the ``TiledRasterLayer`` is floating
            point or not.
    """

    __slots__ = ['pysc', 'layer_type', 'srdd']

    def __init__(self, pysc, layer_type, srdd):
        CachableLayer.__init__(self)
        self.pysc = pysc
        self.layer_type = layer_type
        self.srdd = srdd
        self.is_floating_point_layer = self.srdd.isFloatingPointLayer()

    @property
    def layer_metadata(self):
        """Layer metadata associated with this layer."""

        return Metadata.from_dict(json.loads(self.srdd.layerMetadata()))

    @property
    def zoom_level(self):
        """The zoom level of the Layer. Can be ``None``."""

        return self.srdd.getZoom()

    @classmethod
    def from_numpy_rdd(cls, pysc, layer_type, numpy_rdd, metadata):
        """Create a ``TiledRasterLayer`` from a numpy RDD.

        Args:
            pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
            layer_type (str or :class:`geopyspark.geotrellis.constants.LayerType`): What the spatial type
                of the geotiffs are. This is represented by either constants within ``LayerType`` or by
                a string.
            numpy_rdd (pyspark.RDD): A PySpark RDD that contains tuples of either
                :class:`~geopyspark.geotrellis.SpatialKey` or
                :class:`~geopyspark.geotrellis.SpaceTimeKey` and rasters that are represented by a
                numpy array.
            metadata (:class:`~geopyspark.geotrellis.Metadata`): The ``Metadata`` of
                the ``TiledRasterLayer`` instance.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
        """

        key = map_key_input(LayerType(layer_type).value, True)
        ser = ProtoBufSerializer.create_tuple_serializer(key_type=key)
        reserialized_rdd = numpy_rdd._reserialize(ser)

        if isinstance(metadata, Metadata):
            metadata = metadata.to_dict()

        if layer_type == LayerType.SPATIAL:
            srdd = \
                    pysc._gateway.jvm.geopyspark.geotrellis.SpatialTiledRasterRDD.fromProtoEncodedRDD(
                        reserialized_rdd._jrdd, json.dumps(metadata))
        else:
            srdd = \
                    pysc._gateway.jvm.geopyspark.geotrellis.TemporalTiledRasterRDD.fromProtoEncodedRDD(
                        reserialized_rdd._jrdd, json.dumps(metadata))

        return cls(pysc, layer_type, srdd)

    def to_numpy_rdd(self):
        """Converts a ``TiledRasterLayer`` to a numpy RDD.

        Note:
            Depending on the size of the data stored within the RDD, this can be an exspensive
            operation and should be used with caution.

        Returns:
            RDD
        """

        result = self.srdd.toProtoRDD()
        key = map_key_input(LayerType(self.layer_type).value, True)
        ser = ProtoBufSerializer.create_tuple_serializer(key_type=key)

        return create_python_rdd(self.pysc, result, ser)

    def to_png_rdd(self, color_map):
        """Converts the rasters within this layer to PNGs which are then converted to bytes.
        This is returned as a RDD[(K, bytes)].

        Args:
            color_map (:class:`~geopyspark.geotrellis.color.ColorMap`): A ``ColorMap`` instance
                used to color the PNGs.

        Returns:
            RDD[(K, bytes)]
        """

        result = self.srdd.toPngRDD(color_map.cmap)
        key = map_key_input(LayerType(self.layer_type).value, True)
        ser = ProtoBufSerializer.create_image_rdd_serializer(key_type=key)

        return create_python_rdd(self.pysc, result, ser)

    def bands(self, band):
        """Select a subsection of bands from the ``Tile``\s within the layer.

        Note:
            There could be potential high performance cost if operations are performed
            between two sub-bands of a large data set.

        Note:
            Due to the natue of GeoPySpark's backend, if selecting a band that is out of bounds
            then the error returned will be a ``py4j.protocol.Py4JJavaError`` and not a normal
            Python error.

        Args:
            band (int or tuple or list or range): The band(s) to be selected from the ``Tile``\s.
                Can either be a single ``int``, or a collection of ``int``\s.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer` with the selected bands.
        """

        if isinstance(band, range):
            band = list(band)

        if isinstance(band, (int, tuple, list)):
            result = self.srdd.bands(band)
        else:
            raise TypeError("band must be an int, tuple, or list. Recieved", type(band), "instead.")

        return TiledRasterLayer(self.pysc, self.layer_type, result)

    def map_tiles(self, func):
        """Maps over each ``Tile`` within the layer with a given function.

        Note:
            This operation first needs to deserialize the wrapped ``RDD`` into Python and then
            serialize the ``RDD`` back into a ``TiledRasterRDD`` once the mapping is done. Thus,
            it is advised to chain together operations to reduce performance cost.

        Args:
            func (:class:`~geopyspark.geotrellis.Tile` => :class:`~geopyspark.geotrellis.Tile`): A
                function that takes a ``Tile`` and returns a ``Tile``.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
        """

        python_rdd = self.to_numpy_rdd()

        return TiledRasterLayer.from_numpy_rdd(self.pysc, self.layer_type,
                                               python_rdd.mapValues(lambda tile: func(tile)),
                                               self.layer_metadata)

    def map_cells(self, func):
        """Maps over the cells of each ``Tile`` within the layer with a given function.

        Note:
            This operation first needs to deserialize the wrapped ``RDD`` into Python and then
            serialize the ``RDD`` back into a ``TiledRasterRDD`` once the mapping is done. Thus,
            it is advised to chain together operations to reduce performance cost.

        Args:
            func (cells, nd => cells): A function that takes two arguements: ``cells`` and
                ``nd``. Where ``cells`` is the numpy array and ``nd`` is the ``no_data_value`` of
                the tile. It returns ``cells`` which are the new cells values of the tile
                represented as a numpy array.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
        """

        python_rdd = self.to_numpy_rdd()

        def tile_func(cells, cell_type, no_data_value):
            return Tile(func(cells, no_data_value), cell_type, no_data_value)

        return TiledRasterLayer.from_numpy_rdd(self.pysc, self.layer_type,
                                               python_rdd.mapValues(lambda tile: tile_func(*tile)),
                                               self.layer_metadata)

    def to_geotiff_rdd(self,
                       storage_method=StorageMethod.STRIPED,
                       rows_per_strip=None,
                       tile_dimensions=(256, 256),
                       compression=Compression.NO_COMPRESSION,
                       color_space=ColorSpace.BLACK_IS_ZERO,
                       color_map=None,
                       head_tags=None,
                       band_tags=None):
        """Converts the rasters within this layer to GeoTiffs which are then converted to bytes.
        This is returned as a ``RDD[(K, bytes)]``. Where ``K`` is either ``SpatialKey`` or
        ``SpaceTimeKey``.

        Args:
            storage_method (str or :class:`~geopyspark.geotrellis.constants.StorageMethod`, optional): How
                the segments within the GeoTiffs should be arranged. Default is
                ``StorageMethod.STRIPED``.
            rows_per_strip (int, optional): How many rows should be in each strip segment of the
                GeoTiffs if ``storage_method`` is ``StorageMethod.STRIPED``. If ``None``, then the
                strip size will default to a value that is 8K or less.
            tile_dimensions ((int, int), optional): The length and width for each tile segment of the GeoTiff
                if ``storage_method`` is ``StorageMethod.TILED``. If ``None`` then the default size
                is ``(256, 256)``.
            compression (str or :class:`~geopyspark.geotrellis.constants.Compression`, optional): How the
                data should be compressed. Defaults to ``Compression.NO_COMPRESSION``.
            color_space (str or :class:`~geopyspark.geotrellis.constants.ColorSpace`, optional): How the
                colors should be organized in the GeoTiffs. Defaults to
                ``ColorSpace.BLACK_IS_ZERO``.
            color_map (:class:`~geopyspark.geotrellis.color.ColorMap`, optional): A ``ColorMap``
                instance used to color the GeoTiffs to a different gradient.
            head_tags (dict, optional): A ``dict`` where each key and value is a ``str``.
            band_tags (list, optional): A ``list`` of ``dict``\s where each key and value is a
                ``str``.

            Note:
                For more information on the contents of the tags, see www.gdal.org/gdal_datamodel.html

        Returns:
            RDD[(K, bytes)]
        """

        result = _to_geotiff_rdd(self.pysc, self.srdd, storage_method, rows_per_strip, tile_dimensions,
                                 compression, color_space, color_map, head_tags, band_tags)

        key = map_key_input(LayerType(self.layer_type).value, True)
        ser = ProtoBufSerializer.create_image_rdd_serializer(key_type=key)

        return create_python_rdd(self.pysc, result, ser)

    def convert_data_type(self, new_type, no_data_value=None):
        """Converts the underlying, raster values to a new ``CellType``.

        Args:
            new_type (str or :class:`~geopyspark.geotrellis.constants.CellType`): The data type the
                cells should be to converted to.
            no_data_value (int or float, optional): The value that should be marked as NoData.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`

        Raises:
            ValueError: If ``no_data_value`` is set and the ``new_type`` contains raw values.
            ValueError: If ``no_data_value`` is set and ``new_type`` is a boolean.
        """

        if no_data_value:
            if 'bool' in new_type:
                raise ValueError("Cannot add user defined types to Bool")
            elif 'raw' in new_type:
                raise ValueError("Cannot add user defined types to raw values")

            no_data_constant = CellType(new_type).value + "ud" + str(no_data_value)

            return TiledRasterLayer(self.pysc, self.layer_type,
                                    self.srdd.convertDataType(no_data_constant))
        else:
            return TiledRasterLayer(self.pysc, self.layer_type,
                                    self.srdd.convertDataType(CellType(new_type).value))

    def reproject(self, target_crs, layout=None,
                  resample_method=ResampleMethod.NEAREST_NEIGHBOR):
        """Reproject Layer as tiled raster layer, samples surrounding tiles.

        Args:
            target_crs (str or int): The CRS to reproject to. Can either be the EPSG code,
                well-known name, or a PROJ.4 projection string.
            layout (
                :obj:`~geopyspark.geotrellis.LocalLayout` or
                :obj:`~geopysaprk.geotrellis.GlobalLayout` or
                :obj:`~geopyspark.geotrellis.LayoutDefinition` or
                :class:`~geopyspark.geotrellis.Metadata` or
                :class:`~geopyspark.geotrellis.layer.TiledRasterLayer`, optional): Specify the
                    layout the the tile should be in when it's reprojected. If None, then the
                    layout will be derived from the ``layer_metadata``.
            resample_method (str or :class:`~geopyspark.geotrellis.constants.ResampleMethod`, optional):
                The resample method to use for the reprojection. If none is specified, then
                ``ResampleMethods.NEAREST_NEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`

        Raises:
            TypeError: If reproject could not be done from the given ``layout``.
        """

        if isinstance(target_crs, int):
            target_crs = str(target_crs)

        layout = layout or self.layer_metadata.layout_definition

        if isinstance(layout, (LocalLayout, GlobalLayout)):
            srdd = self.srdd.reproject(layout, target_crs, ResampleMethod(resample_method))

        elif isinstance(layout, TiledRasterLayer):
            layout_definition = layout.layer_metadata.layout_definition

            srdd = self.srdd.reproject(layout_definition.extent._asdict(),
                                       layout_definition.tileLayout._asdict(),
                                       target_crs,
                                       ResampleMethod(resample_method))

        elif isinstance(layout, Metadata):
            layout_definition = layout.layout_definition

            srdd = self.srdd.reproject(layout_definition.extent._asdict(),
                                       layout_definition.tileLayout._asdict(),
                                       target_crs,
                                       ResampleMethod(resample_method))

        elif isinstance(layout, LayoutDefinition):
            srdd = self.srdd.reproject(layout.extent._asdict(),
                                       layout.tileLayout._asdict(),
                                       target_crs,
                                       ResampleMethod(resample_method))
        else:
            raise TypeError("Could not reproject from layout", layout)

        return TiledRasterLayer(self.pysc, self.layer_type, srdd)

    def repartition(self, num_partitions):
        return TiledRasterLayer(self.pysc, self.layer_type, self.srdd.repartition(num_partitions))

    def lookup(self, col, row):
        """Return the value(s) in the image of a particular ``SpatialKey`` (given by col and row).

        Args:
            col (int): The ``SpatialKey`` column.
            row (int): The ``SpatialKey`` row.

        Returns:
            A list of numpy arrays (the tiles)

        Raises:
            ValueError: If using lookup on a non ``LayerType.SPATIAL`` ``TiledRasterLayer``.
            IndexError: If col and row are not within the ``TiledRasterLayer``\'s bounds.
        """
        if self.layer_type != LayerType.SPATIAL:
            raise ValueError("Only TiledRasterLayers with a layer_type of Spatial can use lookup()")

        bounds = self.layer_metadata.bounds
        min_col = bounds.minKey.col
        min_row = bounds.minKey.row
        max_col = bounds.maxKey.col
        max_row = bounds.maxKey.row

        if col < min_col or col > max_col:
            raise IndexError("column out of bounds")
        if row < min_row or row > max_row:
            raise IndexError("row out of bounds")

        array_of_tiles = self.srdd.lookup(col, row)

        return [multibandtile_decoder(tile) for tile in array_of_tiles]

    def tile_to_layout(self, layout_definition, resample_method=ResampleMethod.NEAREST_NEIGHBOR):
        """Cut tiles to a given layout and merge overlapping tiles. This will produce unique keys.

        Args:
            layout_definition (:obj:`~geopyspark.geotrellis.LayoutDefinition`): Specify the
                ``LayoutDefinition`` to cut to.
            resample_method (str or :class:`~geopyspark.geotrellis.constants.ResampleMethod`, optional):
                The resample method to use for the reprojection. If none is specified, then
                ``ResampleMethods.NEAREST_NEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
        """

        srdd = self.srdd.tileToLayout(layout_definition.extent._asdict(),
                                      layout_definition.tileLayout._asdict(),
                                      ResampleMethod(resample_method))

        return TiledRasterLayer(self.pysc, self.layer_type, srdd)

    def pyramid(self, end_zoom, start_zoom=None, resample_method=ResampleMethod.NEAREST_NEIGHBOR):
        """Creates a ``Pyramid`` instance.

        Note:
            This method will only work if the tiles within the layer's layout are sizes of
            multiples of 2.

        Args:
            end_zoom (int): The zoom level where pyramiding should end. Represents
                the level that is most zoomed out.
            start_zoom (int, Optional): The zoom level where pyramiding should begin. Represents
                the level that is most zoomed in. If None, then will use the zoom level from
                :meth:`~geopyspark.geotrellis.rdd.TiledRasterLayer.zoom_level`.
            resample_method (str or :class:`~geopyspark.geotrellis.constants.ResampleMethod`, optional):
                The resample method to use for the reprojection. If none is specified, then
                ``ResampleMethods.NEAREST_NEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.layer.Pyramid`.

        Raises:
            ValueError: If the col and row count is not a power of 2.
        """

        num_cols = self.layer_metadata.tile_layout.tileCols
        num_rows = self.layer_metadata.tile_layout.tileRows

        if (num_cols & (num_cols - 1)) != 0 or (num_rows & (num_rows - 1)) != 0:
            raise ValueError("Tiles dimensions must powers of 2.  Consider `pyramid_non_power_of_two`.")

        if start_zoom:
            start_zoom = start_zoom
        elif self.zoom_level:
            start_zoom = self.zoom_level
        else:
            raise ValueError("No start_zoom given.")

        result = self.srdd.pyramid(start_zoom, end_zoom, ResampleMethod(resample_method))

        return Pyramid([TiledRasterLayer(self.pysc, self.layer_type, srdd) for srdd in result])

    def pyramid_non_power_of_two(self, col_power, row_power, end_zoom, start_zoom=None, resample_method=ResampleMethod.NEAREST_NEIGHBOR):
        """Creates a ``Pyramid`` instance. This will work even if the tiles' sizes are not
        multiples of 2.

        Args:
            col_power (int): The number of tile columns will be two to the power of this number
            row_power (int): The number of tile columns will be two to the power of this number
            end_zoom (int): The zoom level where pyramiding should end. Represents
                the level that is most zoomed out.
            start_zoom (int, Optional): The zoom level where pyramiding should begin. Represents
                the level that is most zoomed in. If None, then will use the zoom level from
                :meth:`~geopyspark.geotrellis.rdd.TiledRasterLayer.zoom_level`.
            resample_method (str or :class:`~geopyspark.geotrellis.constants.ResampleMethod`, optional):
                The resample method to use for the reprojection. If none is specified, then
                ``ResampleMethods.NEAREST_NEIGHBOR`` is used.

        Returns:
            :class:`~geopyspark.geotrellis.layer.Pyramid`.

        Raises:
            ValueError: If the given ``resample_method`` is not known.
        """

        resample_method = ResampleMethod(resample_method)
        new_srdd = self.srdd.resample_to_power_of_two(col_power, row_power, resample_method)
        new_layer = TiledRasterLayer(self.pysc, self.layer_type, new_srdd)

        return new_layer.pyramid(end_zoom=end_zoom, start_zoom=start_zoom, resample_method=resample_method)

    def focal(self, operation, neighborhood=None, param_1=None, param_2=None, param_3=None):
        """Performs the given focal operation on the layers contained in the Layer.

        Args:
            operation (str or :class:`~geopyspark.geotrellis.constants.Operation`): The focal
                operation to be performed.
            neighborhood (str or :class:`~geopyspark.geotrellis.neighborhood.Neighborhood`, optional):
                The type of neighborhood to use in the focal operation. This can be represented by
                either an instance of ``Neighborhood``, or by a constant.
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
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`

        Raises:
            ValueError: If ``operation`` is not a known operation.
            ValueError: If ``neighborhood`` is not a known neighborhood.
            ValueError: If ``neighborhood`` was not set, and ``operation`` is not ``SLOPE`` or
                ``ASPECT``.
        """

        operation = Operation(operation).value

        if isinstance(neighborhood, Neighborhood):
            srdd = self.srdd.focal(operation, neighborhood.name, neighborhood.param_1,
                                   neighborhood.param_2, neighborhood.param_3)

        elif isinstance(neighborhood, (str, nb)):
            param_1 = param_1 or 0.0
            param_2 = param_2 or 0.0
            param_3 = param_3 or 0.0

            srdd = self.srdd.focal(operation, nb(neighborhood).value,
                                   float(param_1), float(param_2), float(param_3))

        elif not neighborhood and operation == Operation.SLOPE.value or operation == Operation.ASPECT.value:
            srdd = self.srdd.focal(operation, nb.SQUARE.value, 1.0, 0.0, 0.0)

        else:
            raise ValueError("neighborhood must be set or the operation must be SLOPE or ASPECT")

        return TiledRasterLayer(self.pysc, self.layer_type, srdd)

    def stitch(self):
        """Stitch all of the rasters within the Layer into one raster.

        Note:
            This can only be used on ``LayerType.SPATIAL`` ``TiledRasterLayer``\s.

        Returns:
            :class:`~geopyspark.geotrellis.Tile`
        """

        if self.layer_type != LayerType.SPATIAL:
            raise ValueError("Only TiledRasterLayers with a layer_type of Spatial can use stitch()")

        value = self.srdd.stitch()
        ser = ProtoBufSerializer.create_value_serializer("Tile")
        return ser.loads(value)[0]

    def save_stitched(self, path, crop_bounds=None, crop_dimensions=None):
        """Stitch all of the rasters within the Layer into one raster.

        Args:
            path (str): The path of the geotiff to save.
            crop_bounds (list, optional): bounds with which to crop the raster before saving.
            crop_dimensions (list, optional): cols and rows of the image to save

        Note:
            This can only be used on ``LayerType.SPATIAL`` ``TiledRasterLayer``\s.
        """

        if self.layer_type != LayerType.SPATIAL:
            raise ValueError("Only TiledRasterLayers with a layer_type of Spatial can use stitch()")

        if crop_bounds:
            if crop_dimensions:
                self.srdd.save_stitched(path, list(crop_bounds), list(crop_dimensions))
            else:
                self.srdd.save_stitched(path, list(crop_bounds))
        elif crop_dimensions:
            raise Exception("crop_dimensions requires crop_bounds")
        else:
            self.srdd.save_stitched(path)

    def mask(self, geometries):
        """Masks the ``TiledRasterLayer`` so that only values that intersect the geometries will
        be available.

        Args:
            geometries (shapely.geometry or [shapely.geometry]): Either a list of, or a single
                shapely geometry/ies to use for the mask/s.

                Note:
                    All geometries must be in the same CRS as the TileLayer.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
        """

        if not isinstance(geometries, list):
            geometries = [geometries]
        wkbs = [shapely.wkb.dumps(g) for g in geometries]
        srdd = self.srdd.mask(wkbs)

        return TiledRasterLayer(self.pysc, self.layer_type, srdd)

    def reclassify(self, value_map, data_type,
                   classification_strategy=ClassificationStrategy.LESS_THAN_OR_EQUAL_TO,
                   replace_nodata_with=None):
        """Changes the cell values of a raster based on how the data is broken up.

        Args:
            value_map (dict): A ``dict`` whose keys represent values where a break should occur and
                its values are the new value the cells within the break should become.
            data_type (type): The type of the values within the rasters. Can either be ``int`` or
                ``float``.
            classification_strategy (str or :class:`~geopyspark.geotrellis.constants.ClassificationStrategy`, optional):
                How the cells should be classified along the breaks. If unspecified, then
                ``ClassificationStrategy.LESS_THAN_OR_EQUAL_TO`` will be used.
            replace_nodata_with (data_type, optional): When remapping values, nodata values must be
                treated separately.  If nodata values are intended to be replaced during the
                reclassify, this variable should be set to the intended value.  If unspecified,
                nodata values will be preserved.

        NOTE:
            NoData symbolizes a different value depending on if ``data_type`` is ``int`` or
            ``float``. For ``int``, the constant ``NO_DATA_INT`` can be used which represents the
            NoData value for ``int`` in GeoTrellis. For ``float``, ``float('nan')`` is used to
            represent NoData.

        Returns:
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
        """

        srdd = _reclassify(self.srdd, value_map, data_type,
                           ClassificationStrategy(classification_strategy).value, replace_nodata_with)

        return TiledRasterLayer(self.pysc, self.layer_type, srdd)

    def get_min_max(self):
        """Returns the maximum and minimum values of all of the rasters in the Layer.

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
            :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
        """

        srdd = self.srdd.normalize(old_min, old_max, new_min, new_max)

        return TiledRasterLayer(self.pysc, self.layer_type, srdd)

    @staticmethod
    def _process_polygonal_summary(geometry, operation):
        if isinstance(geometry, (Polygon, MultiPolygon)):
            geometry = shapely.wkb.dumps(geometry)
        if not isinstance(geometry, bytes):
            raise TypeError("Expected geometry to be bytes but given this instead", type(geometry))

        return operation(geometry)

    def polygonal_min(self, geometry, data_type):
        """Finds the min value that is contained within the given geometry.

        Args:
            geometry (shapely.geometry.Polygon or shapely.geometry.MultiPolygon or bytes): A
                Shapely ``Polygon`` or ``MultiPolygon`` that represents the area where the summary
                should be computed; or a WKB representation of the geometry.
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
            geometry (shapely.geometry.Polygon or shapely.geometry.MultiPolygon or bytes): A
                Shapely ``Polygon`` or ``MultiPolygon`` that represents the area where the summary
                should be computed; or a WKB representation of the geometry.
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
            geometry (shapely.geometry.Polygon or shapely.geometry.MultiPolygon or bytes): A
                Shapely ``Polygon`` or ``MultiPolygon`` that represents the area where the summary
                should be computed; or a WKB representation of the geometry.
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
            geometry (shapely.geometry.Polygon or shapely.geometry.MultiPolygon or bytes): A
                Shapely ``Polygon`` or ``MultiPolygon`` that represents the area where the summary
                should be computed; or a WKB representation of the geometry.

        Returns:
            ``float``
        """

        return self._process_polygonal_summary(geometry, self.srdd.polygonalMean)

    def get_quantile_breaks(self, num_breaks):
        """Returns quantile breaks for this Layer.

        Args:
            num_breaks (int): The number of breaks to return.

        Returns:
            ``[float]``
        """
        return list(self.srdd.quantileBreaks(num_breaks))

    def get_quantile_breaks_exact_int(self, num_breaks):
        """Returns quantile breaks for this Layer.
        This version uses the ``FastMapHistogram``, which counts exact integer values.
        If your layer has too many values, this can cause memory errors.

        Args:
            num_breaks (int): The number of breaks to return.

        Returns:
            ``[int]``
        """
        return list(self.srdd.quantileBreaksExactInt(num_breaks))

    def get_histogram(self):
        """Creates a ``Histogram`` from the values within this layer.

        Returns:
            :class:`~geopyspark.geotrellis.histogram.Histogram`
        """

        if self.is_floating_point_layer:
            histogram = self.srdd.getDoubleHistograms()
        else:
            histogram = self.srdd.getIntHistograms()

        return Histogram(histogram)

    def _process_operation(self, value, operation):
        if isinstance(value, int) or isinstance(value, float):
            srdd = operation(value)
        elif isinstance(value, TiledRasterLayer):
            if self.layer_type != value.layer_type:
                raise ValueError("Both TiledRasterLayers need to have the same layer_type")

            if self.layer_metadata.tile_layout != value.layer_metadata.tile_layout:
                raise ValueError("Both TiledRasterLayers need to have the same layout")

            srdd = operation(value.srdd)
        elif isinstance(value, list):
            srdd = operation(list(map(lambda x: x.srdd, value)))
        else:
            raise TypeError("Local operation cannot be performed with", value)

        return TiledRasterLayer(self.pysc, self.layer_type, srdd)

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

    def __str__(self):
        return "TiledRasterLayer(layer_type={}, zoom_level={}, is_floating_point_layer={})".format(
            self.layer_type, self.zoom_level, self.is_floating_point_layer)

    def __repr__(self):
        return "TiledRasterLayer(layer_type={}, zoom_level={}, is_floating_point_layer={})".format(
            self.layer_type, self.zoom_level, self.is_floating_point_layer)


def _common_entries(*dcts):
    """Zip two dictionaries together by keys"""
    for i in set(dcts[0]).intersection(*dcts[1:]):
        yield (i,) + tuple(d[i] for d in dcts)


class Pyramid(CachableLayer):
    """Contains a list of ``TiledRasterLayer``\s that make up a tile pyramid.
    Each layer represents a level within the pyramid. This class is used when creating
    a tile server.

    Map algebra can performed on instances of this class.

    Args:
        levels (list or dict): A list of ``TiledRasterLayer``\s or a dict of
            ``TiledRasterLayer``\s where the value is the layer itself and the key is
            its given zoom level.

    Attributes:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        layer_type (str or :class:`~geopyspark.geotrellis.constants.LayerType`): What the spatial
            type of the geotiffs are.
        levels (dict): A dict of ``TiledRasterLayer``\s where the value is the layer itself
            and the key is its given zoom level.
        max_zoom (int): The highest zoom level of the pyramid.
        is_cached (bool): Signals whether or not the internal RDDs are cached. Default
            is ``False``.
        histogram (:class:`~geopyspark.geotrellis.histogram.Histogram`): The ``Histogram``
            that represents the layer with the max zoomw. Will not be calculated unless the
            :meth:`~geopyspark.geotrellis.layer.Pyramid.get_histogram` method is used.
            Otherwise, its value is ``None``.

    Raises:
        TypeError: If ``levels`` is neither a list or dict.
    """

    __slots__ = ['pysc', 'layer_type', 'levels', 'max_zoom', 'is_cached', 'histogram']

    def __init__(self, levels):
        if isinstance(levels, dict):
            levels = levels
        elif isinstance(levels, list):
            levels = dict([(l.zoom_level, l) for l in levels])
        else:
            raise TypeError("levels are neither list or dictionary")

        self.levels = levels
        self.max_zoom = max(self.levels.keys())
        self.pysc = levels[self.max_zoom].pysc
        self.layer_type = levels[self.max_zoom].layer_type
        self.is_cached = False
        self.histogram = None

    def wrapped_rdds(self):
        """Returns a list of the wrapped, Scala RDDs within each layer of the pyramid.

        Returns:
            [org.apache.spark.rdd.RDD]
        """

        return [rdd.srdd for rdd in self.levels.values()]

    def get_histogram(self):
        """Calculates the ``Histogram`` for the layer with the max zoom.

        Returns:
            :class:`~geopyspark.geotrellis.histogram.Histogram`
        """

        if not self.histogram:
            self.histogram = self.levels[self.max_zoom].get_histogram()
        return self.histogram

    # Keep it in non rendered form so we can do map algebra operations to it

    def __add__(self, value):
        if isinstance(value, Pyramid):
            return Pyramid({k: l.__add__(r) for k, l, r in _common_entries(self.levels, value.levels)})
        else:
            return Pyramid({k: l.__add__(value) for k, l in self.levels.items()})

    def __radd__(self, value):
        if isinstance(value, Pyramid):
            return Pyramid({k: l.__radd__(r) for k, l, r in _common_entries(self.levels, value.levels)})
        else:
            return Pyramid({k: l.__radd__(value) for k, l in self.levels.items()})

    def __sub__(self, value):
        if isinstance(value, Pyramid):
            return Pyramid({k: l.__sub__(r) for k, l, r in _common_entries(self.levels, value.levels)})
        else:
            return Pyramid({k: l.__sub__(value) for k, l in self.levels.items()})

    def __rsub__(self, value):
        if isinstance(value, Pyramid):
            return Pyramid({k: l.__rsub__(r) for k, l, r in _common_entries(self.levels, value.levels)})
        else:
            return Pyramid({k: l.__rsub__(value) for k, l in self.levels.items()})

    def __mul__(self, value):
        if isinstance(value, Pyramid):
            return Pyramid({k: l.__mul__(r) for k, l, r in _common_entries(self.levels, value.levels)})
        else:
            return Pyramid({k: l.__mul__(value) for k, l in self.levels.items()})

    def __rmul__(self, value):
        if isinstance(value, Pyramid):
            return Pyramid({k: l.__rmul__(r) for k, l, r in _common_entries(self.levels, value.levels)})
        else:
            return Pyramid({k: l.__rmul__(value) for k, l in self.levels.items()})

    def __truediv__(self, value):
        if isinstance(value, Pyramid):
            return Pyramid({k: l.__truediv__(r) for k, l, r in _common_entries(self.levels, value.levels)})
        else:
            return Pyramid({k: l.__truediv__(value) for k, l in self.levels.items()})

    def __rtruediv__(self, value):
        if isinstance(value, Pyramid):
            return Pyramid({k: l.__rtruediv__(r) for k, l, r in _common_entries(self.levels, value.levels)})
        else:
            return Pyramid({k: l.__rtruediv__(value) for k, l in self.levels.items()})

    def __str__(self):
        return "Pyramid(layer_type={}, max_zoom={}, num_levels={}, is_cached={})".format(
            self.layer_type, self.max_zoom, len(self.levels), self.is_cached)

    def __repr__(self):
        return "Pyramid(layer_type={}, max_zoom={}, num_levels={}, is_cached={})".format(
            self.layer_type, self.max_zoom, len(self.levels), self.is_cached)
