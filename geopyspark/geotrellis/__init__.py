"""This subpackage contains the code that reads, writes, and processes data using GeoTrellis."""
from collections import namedtuple
import warnings
import datetime
import functools
import datetime
from shapely.geometry import box

from geopyspark import get_spark_context
from geopyspark.geotrellis.constants import CellType, NO_DATA_INT


_EPOCH = datetime.datetime.utcfromtimestamp(0)

def _convert_to_unix_time(date_time):
    return int((date_time - _EPOCH).total_seconds() * 1000)


def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used."""

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter('always', DeprecationWarning) #turn off filter
        warnings.warn("Call to deprecated function {}.".format(func.__name__),
                      category=DeprecationWarning, stacklevel=2)
        warnings.simplefilter('default', DeprecationWarning) #reset filter
        return func(*args, **kwargs)

    return new_func


def crs_to_proj4(crs):
    """Converts a given CRS to a Proj4 string.

    Args:
        crs (str or int): Target CRS of reprojection. Either EPSG code, well-known name, or a
            PROJ.4 string. If ``None``, no reproject will be perfomed.

    Returns:
        str
    """

    if not isinstance(crs, str):
        crs = str(crs)

    pysc = get_spark_context()
    scala_crs = pysc._gateway.jvm.geopyspark.geotrellis.TileLayer.getCRS(crs).get()

    return scala_crs.toProj4String()


class Tile(namedtuple("Tile", 'cells cell_type no_data_value')):
    """Represents a raster in GeoPySpark.

    Note:
        All rasters in GeoPySpark are represented as having multiple bands, even if the original
        raster just contained one.

    Args:
        cells (nd.array): The raster data itself. It is contained within a NumPy array.
        data_type (str): The data type of the values within ``data`` if they were in Scala.
        no_data_value: The value that represents no data value in the raster. This can be
            represented by a variety of types depending on the value type of the raster.

    Attributes:
        cells (nd.array): The raster data itself. It is contained within a NumPy array.
        data_type (str): The data type of the values within ``data`` if they were in Scala.
        no_data_value: The value that represents no data value in the raster. This can be
            represented by a variety of types depending on the value type of the raster.
    """

    __slots__ = []

    @staticmethod
    def dtype_to_cell_type(dtype):
        """Converts a ``np.dtype`` to the corresponding GeoPySpark ``cell_type``.

        Note:
            ``bool``, ``complex64``, ``complex128``, and ``complex256``, are currently not
            supported ``np.dtype``\s.

        Args:
            dtype (np.dtype): The ``dtype`` of the numpy array.

        Returns:
            str. The GeoPySpark ``cell_type`` equivalent of the ``dtype``.

        Raises:
            TypeError: If the given ``dtype`` is not a supported data type.
        """

        name = dtype.name

        if name == 'int8':
            return 'BYTE'
        elif name == 'uint8':
            return 'UBYTE'
        elif name == 'int16':
            return 'SHORT'
        elif name == 'uint16':
            return 'USHORT'
        elif name == 'int32':
            return 'INT'
        elif name in ['uint32', 'float16', 'float32']:
            return 'FLOAT'
        elif name in ['int64', 'uint64', 'float64']:
            return 'DOUBLE'
        else:
            raise TypeError(name, "Is not a supported data type.")

    @classmethod
    def from_numpy_array(cls, numpy_array, no_data_value=None):
        """Creates an instance of ``Tile`` from a numpy array.

        Args:
            numpy_array (np.array): The numpy array to be used to represent the cell values
                of the ``Tile``.

                Note:
                    GeoPySpark does not support arrays with the following data types: ``bool``,
                    ``complex64``, ``complex128``, and ``complex256``.

            no_data_value (optional): The value that represents no data value in the raster.
                This can be represented by a variety of types depending on the value type of
                the raster. If not given, then the value will be ``None``.

        Returns:
            :class:`~geopyspark.geotrellis.Tile`
        """

        return cls(numpy_array, cls.dtype_to_cell_type(numpy_array.dtype), no_data_value)


class Log(object):
    @classmethod
    def debug(cls, pysc, s):
        pysc._gateway.jvm.geopyspark.geotrellis.Log.debug(s)

    @classmethod
    def info(cls, pysc, s):
        pysc._gateway.jvm.geopyspark.geotrellis.Log.info(s)

    @classmethod
    def warn(cls, pysc, s):
        pysc._gateway.jvm.geopyspark.geotrellis.Log.warn(s)

    @classmethod
    def error(cls, pysc, s):
        pysc._gateway.jvm.geopyspark.geotrellis.Log.error(s)


class Extent(namedtuple("Extent", 'xmin ymin xmax ymax')):
    """
    The "bounding box" or geographic region of an area on Earth a raster represents.

    Args:
        xmin (float): The minimum x coordinate.
        ymin (float): The minimum y coordinate.
        xmax (float): The maximum x coordinate.
        ymax (float): The maximum y coordinate.

    Attributes:
        xmin (float): The minimum x coordinate.
        ymin (float): The minimum y coordinate.
        xmax (float): The maximum x coordinate.
        ymax (float): The maximum y coordinate.
    """

    __slots__ = []

    @classmethod
    def from_polygon(cls, polygon):
        """Creates a new instance of ``Extent`` from a Shapely Polygon.

        The new ``Extent`` will contain the min and max coordinates of the Polygon;
        regardless of the Polygon's shape.

        Args:
            polygon (shapely.geometry.Polygon): A Shapely Polygon.

        Returns:
            :class:`~geopyspark.geotrellis.Extent`
        """

        return cls(*polygon.bounds)

    @property
    def to_polygon(self):
        """Converts this instance to a Shapely Polygon.

        The resulting Polygon will be in the shape of a box.

        Returns:
            ``shapely.geometry.Polygon``
        """

        return box(*self)


class ProjectedExtent(namedtuple("ProjectedExtent", 'extent epsg proj4')):
    """Describes both the area on Earth a raster represents in addition to its CRS.

    Args:
        extent (:class:`~geopyspark.geotrellis.Extent`): The area the raster represents.
        epsg (int, optional): The EPSG code of the CRS.
        proj4 (str, optional): The Proj.4 string representation of the CRS.

    Attributes:
        extent (:class:`~geopyspark.geotrellis.Extent`): The area the raster represents.
        epsg (int, optional): The EPSG code of the CRS.
        proj4 (str, optional): The Proj.4 string representation of the CRS.

    Note:
        Either ``epsg`` or ``proj4`` must be defined.
    """

    __slots__ = []

    def __new__(cls, extent, epsg=None, proj4=None):
        return super(ProjectedExtent, cls).__new__(cls, extent, epsg, proj4)

    def _asdict(self):
        if isinstance(self.extent, dict):
            return {'extent': self.extent, 'epsg': self.epsg, 'proj4': self.proj4}
        else:
            return {'extent': self.extent._asdict(), 'epsg': self.epsg, 'proj4': self.proj4}


class TemporalProjectedExtent(namedtuple("TemporalProjectedExtent", 'extent instant epsg proj4')):
    """Describes the area on Earth the raster represents, its CRS, and the time the data was
    collected.

    Args:
        extent (:class:`~geopyspark.geotrellis.Extent`): The area the raster represents.
        instant (``datetime.datetime``): The time stamp of the raster.
        epsg (int, optional): The EPSG code of the CRS.
        proj4 (str, optional): The Proj.4 string representation of the CRS.

    Attributes:
        extent (:class:`~geopyspark.geotrellis.Extent`): The area the raster represents.
        instant (``datetime.datetime``): The time stamp of the raster.
        epsg (int, optional): The EPSG code of the CRS.
        proj4 (str, optional): The Proj.4 string representation of the CRS.

    Note:
        Either ``epsg`` or ``proj4`` must be defined.
    """

    __slots__ = []

    def __new__(cls, extent, instant, epsg=None, proj4=None):
        return super(TemporalProjectedExtent, cls).__new__(cls, extent, instant, epsg, proj4)

    def _asdict(self):
        if isinstance(self.extent, dict):
            return {'extent': self.extent, 'instant': self.instant, 'epsg': self.epsg,
                    'proj4': self.proj4}
        else:
            return {'extent': self.extent._asdict(), 'instant': self.instant, 'epsg': self.epsg,
                    'proj4': self.proj4}


GlobalLayout = namedtuple("GlobalLayout", 'tile_size zoom threshold')
"""TileLayout type that spans global CRS extent.

When passed in place of LayoutDefinition it signifies that a LayoutDefinition instance should be
constructed such that it fits the global CRS extent. The cell resolution of resulting layout will
be one of resolutions implied by power of 2 pyramid for that CRS. Tiling to this layout will
likely result in either up-sampling or down-sampling the source raster.

Args:
    tile_size (int): The number of columns and row pixels in each tile.
    zoom (int, optional): Override the zoom level in power of 2 pyramid.
    threshold(float, optional): The percentage difference between a cell size and a zoom level and
        the resolution difference between that zoom level and the next that is tolerated to snap to
        the lower-resolution zoom level. For example, if this paramter is 0.1, that means we're
        willing to downsample rasters with a higher resolution in order to fit them to some zoom
        level Z, if the difference is resolution is less than or equal to 10% the difference between
        the resolutions of zoom level Z and zoom level Z+1.

Returns:
    :obj:`~geopyspark.geotrellis.GlobalLayout`
"""
GlobalLayout.__new__.__defaults__ = (256, None, 0.1)


class LocalLayout(namedtuple("LocalLayout", 'tile_cols tile_rows')):
    """TileLayout type that snaps the layer extent.

    When passed in place of LayoutDefinition it signifies that a LayoutDefinition instances should
    be constructed over the envelope of the layer pixels with given tile size. Resulting TileLayout
    will match the cell resolution of the source rasters.

    Args:
        tile_size (int, optional): The number of columns and row pixels in each tile. If this
            is ``None``, then the sizes of each tile will be set using ``tile_cols`` and
            ``tile_rows``.
        tile_cols (int, optional): The number of column pixels in each tile. This supersedes
            ``tile_size``. Meaning if this and ``tile_size`` are set, then this will be used for
            the number of colunn pixles. If ``None``, then the number of column pixels will
            default to 256.
        tile_rows (int, optional): The number of rows pixels in each tile. This supersedes
            ``tile_size``. Meaning if this and ``tile_size`` are set, then this will be used for
            the number of row pixles. If ``None``, then the number of row pixels will
            default to 256.

    Attributes:
        tile_cols (int): The number of column pixels in each tile
        tile_rows (int): The number of rows pixels in each tile. This supersedes
    """

    __slots__ = []

    def __new__(cls, tile_size=None, tile_cols=None, tile_rows=None):
        tile_cols = tile_cols or tile_size or 256
        tile_rows = tile_rows or tile_size or 256

        return super(cls, LocalLayout).__new__(cls, tile_cols, tile_rows)


TileLayout = namedtuple("TileLayout", 'layoutCols layoutRows tileCols tileRows')
"""
Describes the grid in which the rasters within a Layer should be laid out.

Args:
    layoutCols (int): The number of columns of rasters that runs east to west.
    layoutRows (int): The number of rows of rasters that runs north to south.
    tileCols (int): The number of columns of pixels in each raster that runs east to west.
    tileRows (int): The number of rows of pixels in each raster that runs north to south.

Returns:
    :obj:`~geopyspark.geotrellis.TileLayout`
"""


LayoutDefinition = namedtuple("LayoutDefinition", 'extent tileLayout')
"""
Describes the layout of the rasters within a Layer and how they are projected.

Args:
    extent (:class:`~geopyspark.geotrellis.Extent`): The ``Extent`` of the layout.
    tileLayout (:obj:`~geopyspark.geotrellis.TileLayout`): The ``TileLayout`` of
        how the rasters within the Layer.

Returns:
    :obj:`~geopyspark.geotrellis.LayoutDefinition`
"""


SpatialKey = namedtuple("SpatialKey", 'col row')
"""
Represents the position of a raster within a grid.
This grid is a 2D plane where raster positions are represented by a pair of coordinates.

Args:
    col (int): The column of the grid, the numbers run east to west.
    row (int): The row of the grid, the numbers run north to south.

Returns:
    :obj:`~geopyspark.geotrellis.SpatialKey`
"""


SpaceTimeKey = namedtuple("SpaceTimeKey", 'col row instant')
"""
Represents the position of a raster within a grid.
This grid is a 3D plane where raster positions are represented by a pair of coordinates as well
as a z value that represents time.

Args:
    col (int): The column of the grid, the numbers run east to west.
    row (int): The row of the grid, the numbers run north to south.
    instant (``datetime.datetime``): The time stamp of the raster.

Returns:
    :obj:`~geopyspark.geotrellis.SpaceTimeKey`
"""

RasterizerOptions = namedtuple("RasterizeOption", 'includePartial sampleType')
"""Represents options available to geometry rasterizer

Args:
    includePartial (bool): Include partial pixel intersection (default: True)
    sampleType (str): 'PixelIsArea' or 'PixelIsPoint' (default: 'PixelIsPoint')
"""
RasterizerOptions.__new__.__defaults__ = (True, 'PixelIsPoint')


class Bounds(namedtuple("Bounds", 'minKey maxKey')):
    """
    Represents the grid that covers the area of the rasters in a Layer on a grid.

    Args:
        minKey (:obj:`~geopyspark.geotrellis.SpatialKey` or :obj:`~geopyspark.geotrellis.SpaceTimeKey`):
            The smallest ``SpatialKey`` or ``SpaceTimeKey``.
        minKey (:obj:`~geopyspark.geotrellis.SpatialKey` or :obj:`~geopyspark.geotrellis.SpaceTimeKey`):
            The largest ``SpatialKey`` or ``SpaceTimeKey``.

    Returns:
        :class:`~geopyspark.geotrellis.Bounds`
    """

    __slots__ = []

    def _asdict(self):
        min_key_dict = self.minKey._asdict()
        max_key_dict = self.maxKey._asdict()

        if hasattr(self.minKey, 'instant'):
            min_key_dict['instant'] = _convert_to_unix_time(min_key_dict['instant'])
            max_key_dict['instant'] = _convert_to_unix_time(max_key_dict['instant'])

        return {'minKey': min_key_dict, 'maxKey': max_key_dict}


class Metadata(object):
    """Information of the values within a ``RasterLayer`` or ``TiledRasterLayer``.
    This data pertains to the layout and other attributes of the data within the classes.

    Args:
        bounds (:obj:`~geopyspark.geotrellis.Bounds`): The ``Bounds`` of the
            values in the class.
        crs (str or int): The ``CRS`` of the data. Can either be the EPSG code, well-known name, or
            a PROJ.4 projection string.
        cell_type (str or :class:`~geopyspark.geotrellis.constants.CellType`): The data type of the
            cells of the rasters.
        extent (:class:`~geopyspark.geotrellis.Extent`): The ``Extent`` that covers
            the all of the rasters.
        layout_definition (:obj:`~geopyspark.geotrellis.LayoutDefinition`): The
            ``LayoutDefinition`` of all rasters.

    Attributes:
        bounds (:obj:`~geopyspark.geotrellis.Bounds`): The ``Bounds`` of the values in the class.
        crs (str or int): The CRS of the data. Can either be the EPSG code, well-known name, or
            a PROJ.4 projection string.
        cell_type (str): The data type of the cells of the rasters.
        no_data_value (int or float or None): The noData value of the rasters within the layer.
            This can either be ``None``, an ``int``, or a ``float`` depending on the ``cell_type``.
        extent (:class:`~geopyspark.geotrellis.Extent`): The ``Extent`` that covers
            the all of the rasters.
        tile_layout (:obj:`~geopyspark.geotrellis.TileLayout`): The ``TileLayout``
            that describes how the rasters are orginized.
        layout_definition (:obj:`~geopyspark.geotrellis.LayoutDefinition`): The
            ``LayoutDefinition`` of all rasters.
    """

    def __init__(self, bounds, crs, cell_type, extent, layout_definition):
        self.bounds = bounds
        self.crs = crs

        if isinstance(cell_type, CellType):
            self.cell_type = CellType(cell_type).value
        else:
            self.cell_type = cell_type

        self.extent = extent
        self.tile_layout = layout_definition.tileLayout
        self.layout_definition = layout_definition

        if 'raw' in self.cell_type or 'bool' in self.cell_type:
            self.no_data_value = None
        elif 'ud' in self.cell_type:
            value = self.cell_type.split("ud")[1]

            if "float" in self.cell_type:
                self.no_data_value = float(value)
            else:
                self.no_data_value = int(value)
        else:
            if self.cell_type == CellType.INT8.value:
                self.no_data_value = -128
            elif self.cell_type == CellType.UINT8.value or self.cell_type == CellType.UINT16.value:
                self.no_data_value = 0
            elif self.cell_type == CellType.INT16.value:
                self.no_data_value = -32768
            elif self.cell_type == CellType.INT32.value:
                self.no_data_value = NO_DATA_INT
            else:
                self.no_data_value = float('nan')

    @classmethod
    def from_dict(cls, metadata_dict):
        """Creates ``Metadata`` from a dictionary.

        Args:
            metadata_dict (dict): The ``Metadata`` of a ``RasterLayer`` or ``TiledRasterLayer``
                instance that is in ``dict`` form.

        Returns:
            :class:`~geopyspark.geotrellis.Metadata`
        """

        crs = metadata_dict['crs']
        cell_type = metadata_dict['cellType']

        bounds_dict = metadata_dict['bounds']

        if len(bounds_dict['minKey']) == 2:
            min_key = SpatialKey(**bounds_dict['minKey'])
            max_key = SpatialKey(**bounds_dict['maxKey'])
        else:
            scala_min_key = bounds_dict['minKey']
            scala_max_key = bounds_dict['maxKey']

            scala_min_key['instant'] = datetime.datetime.utcfromtimestamp(scala_min_key['instant'] / 1000)
            scala_max_key['instant'] = datetime.datetime.utcfromtimestamp(scala_max_key['instant'] / 1000)

            min_key = SpaceTimeKey(**scala_min_key)
            max_key = SpaceTimeKey(**scala_max_key)

        bounds = Bounds(min_key, max_key)
        extent = Extent(**metadata_dict['extent'])

        layout_definition = LayoutDefinition(
            Extent(**metadata_dict['layoutDefinition']['extent']),
            TileLayout(**metadata_dict['layoutDefinition']['tileLayout']))

        return cls(bounds, crs, cell_type, extent, layout_definition)

    def to_dict(self):
        """Converts this instance to a ``dict``.

        Returns:
            ``dict``
        """

        if not hasattr(self, '_metadata_dict'):
            self._metadata_dict = {
                'bounds': self.bounds._asdict(),
                'crs': self.crs,
                'cellType': self.cell_type,
                'extent': self.extent._asdict(),
                'layoutDefinition': {
                    'extent': self.layout_definition.extent._asdict(),
                    'tileLayout': self.tile_layout._asdict()
                }
            }

        return self._metadata_dict

    def __repr__(self):
        return "Metadata({}, {}, {}, {}, {}, {}, {})".format(self.bounds, self.cell_type,
                                                             self.no_data_value, self.crs,
                                                             self.extent, self.tile_layout,
                                                             self.layout_definition)


    def __str__(self):
        return ("Metadata("
                "bounds={}"
                "cellType={}"
                "noDataValue={}"
                "crs={}"
                "extent={}"
                "tileLayout={}"
                "layoutDefinition={})").format(self.bounds, self.cell_type,
                                               self.no_data_value, self.crs, self.extent,
                                               self.tile_layout, self.layout_definition)


__all__ = ["Tile", "Extent", "ProjectedExtent", "TemporalProjectedExtent", "SpatialKey", "SpaceTimeKey",
           "Metadata", "TileLayout", "GlobalLayout", "LocalLayout", "LayoutDefinition", "Bounds", "RasterizerOptions"]

from . import catalog
from . import color
from . import constants
from . import converters
from . import geotiff
from . import histogram
from . import layer
from . import neighborhood
from . import tms

from .catalog import *
from .color import *
from .constants import *
from .converters import *
from .cost_distance import *
from .euclidean_distance import *
from .hillshade import *
from .histogram import *
from .layer import *
from .neighborhood import *
from .rasterize import *
from .tms import *

__all__ += catalog.__all__
__all__ += color.__all__
__all__ += constants.__all__
__all__ += ['cost_distance']
__all__ += ['euclidean_distance']
__all__ += ['geotiff']
__all__ += ['hillshade']
__all__ += histogram.__all__
__all__ += layer.__all__
__all__ += neighborhood.__all__
__all__ += ['rasterize']
__all__ += tms.__all__
