"""This subpackage contains the code that reads, writes, and processes data using GeoTrellis."""
from collections import namedtuple
from shapely.geometry import box
import warnings
import functools

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


Tile = namedtuple("Tile", 'cells cell_type no_data_value')
"""Represents a raster in GeoPySpark.

    Note: All rasters in GeoPySpark are represented as having multiple bands,
    even if the original raster just contained one.

    Args:
        cells (nd.array): The raster data itself. It is contained within a NumPy array.
        data_type (str): The data type of the values within ``data`` if they were in Scala.
        no_data_value: The value that represents no data in raster. This can be
            represented by a variety of types depending on the value type of the raster.

    Returns:
        :obj:`~geopyspark.geotrellis.Tile`
"""


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

    @classmethod
    def from_protobuf_projected_extent(cls, proto_projected_extent):

        if proto_projected_extent.crs.epsg is not 0:
            return cls(extent=Extent.from_protobuf_extent(proto_projected_extent.extent),
                       epsg=proto_projected_extent.crs.epsg)
        else:
            return cls(extent=Extent.from_protobuf_extent(proto_projected_extent.extent),
                       proj4=proto_projected_extent.crs.proj4)

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
        instance (int): The time stamp of the raster.
        epsg (int, optional): The EPSG code of the CRS.
        proj4 (str, optional): The Proj.4 string representation of the CRS.

    Attributes:
        extent (:class:`~geopyspark.geotrellis.Extent`): The area the raster represents.
        instance (int): The time stamp of the raster.
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
    instance (int): The time stamp of the raster.

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
        if isinstance(self.minKey, dict):
            min_key_dict = self.minKey
        else:
            min_key_dict = self.minKey._asdict()

        if isinstance(self.maxKey, dict):
            max_key_dict = self.maxKey
        else:
            max_key_dict = self.maxKey._asdict()

        return {'minKey': min_key_dict, 'maxKey': max_key_dict}


class Metadata(object):
    """Information of the values within a ``RasterLayer`` or ``TiledRasterLayer``.
    This data pertains to the layout and other attributes of the data within the classes.

    Args:
        bounds (:obj:`~geopyspark.geotrellis.Bounds`): The ``Bounds`` of the
            values in the class.
        crs (str or int): The ``CRS`` of the data. Can either be the EPSG code, well-known name, or
            a PROJ.4 projection string.
        cell_type (str): The data type of the cells of the rasters.
        extent (:class:`~geopyspark.geotrellis.Extent`): The ``Extent`` that covers
            the all of the rasters.
        layout_definition (:obj:`~geopyspark.geotrellis.LayoutDefinition`): The
            ``LayoutDefinition`` of all rasters.

    Attributes:
        bounds (:obj:`~geopyspark.geotrellis.Bounds`): The ``Bounds`` of the values in the class.
        crs (str or int): The CRS of the data. Can either be the EPSG code, well-known name, or
            a PROJ.4 projection string.
        cell_type (str): The data type of the cells of the rasters.
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
        self.cell_type = cell_type
        self.extent = extent
        self.tile_layout = layout_definition.tileLayout
        self.layout_definition = layout_definition

    @classmethod
    def from_dict(cls, metadata_dict):
        """Creates ``Metadata`` from a dictionary.

        Args:
            metadata_dict (dict): The ``Metadata`` of a ``RasterLayer`` or ``TiledRasterLayer``
                instance that is in ``dict`` form.

        Returns:
            :class:`~geopyspark.geotrellis.Metadata`
        """

        cls._metadata_dict = metadata_dict

        crs = metadata_dict['crs']
        cell_type = metadata_dict['cellType']

        bounds_dict = metadata_dict['bounds']

        if len(bounds_dict['minKey']) == 2:
            min_key = SpatialKey(**bounds_dict['minKey'])
            max_key = SpatialKey(**bounds_dict['maxKey'])
        else:
            min_key = SpaceTimeKey(**bounds_dict['minKey'])
            max_key = SpaceTimeKey(**bounds_dict['maxKey'])

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
        return "Metadata({}, {}, {}, {}, {}, {})".format(self.bounds, self.cell_type,
                                                         self.crs, self.extent,
                                                         self.tile_layout, self.layout_definition)


    def __str__(self):
        return ("Metadata("
                "bounds={}"
                "cellType={}"
                "crs={}"
                "extent={}"
                "tileLayout={}"
                "layoutDefinition={})").format(self.bounds, self.cell_type,
                                               self.crs, self.extent,
                                               self.tile_layout, self.layout_definition)


__all__ = ["catalog", "geotiff", "layer", "cost_distance", "hillshade", "euclidean_distance",
           "rasterize", "tms"]

from . import converters
