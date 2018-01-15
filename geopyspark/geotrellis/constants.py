"""Constants that are used by ``geopyspark.geotrellis`` classes, methods, and functions."""
from enum import Enum, IntEnum


__all__ = ['NO_DATA_INT', 'LayerType', 'IndexingMethod', 'ResampleMethod', 'TimeUnit',
           'Operation', 'Neighborhood', 'ClassificationStrategy', 'CellType', 'ColorRamp',
           'DEFAULT_MAX_TILE_SIZE', 'DEFAULT_PARTITION_BYTES', 'DEFAULT_CHUNK_SIZE',
           'DEFAULT_GEOTIFF_TIME_TAG', 'DEFAULT_GEOTIFF_TIME_FORMAT', 'DEFAULT_S3_CLIENT',
           'StorageMethod', 'ColorSpace', 'Compression', 'Unit', 'Partitioner']


"""The NoData value for ints in GeoTrellis."""
NO_DATA_INT = -2147483648


"""The default size of each tile in the resulting layer."""
DEFAULT_MAX_TILE_SIZE = 256


"""The default byte size of each partition."""
DEFAULT_PARTITION_BYTES = 1281 * 1024 * 1024


"""The default number of bytes that should be read in at a time."""
DEFAULT_CHUNK_SIZE = 65536


"""The default name of the GeoTiff tag that contains the timestamp for the tile."""
DEFAULT_GEOTIFF_TIME_TAG = "TIFFTAG_DATETIME"


"""The default pattern that will be parsed from the timeTag."""
DEFAULT_GEOTIFF_TIME_FORMAT = "yyyy:MM:dd HH:mm:ss"


"""The default S3 Client to use when reading layers in."""
DEFAULT_S3_CLIENT = "default"


class LayerType(Enum):
    """The type of the key within the tuple of the wrapped RDD."""

    """
    Indicates that the RDD contains ``(K, V)`` pairs, where the ``K`` has a spatial attribute,
    but no time value. Both :class:`~geopyspark.geotrellis.ProjectedExtent` and
    :class:`~geopyspark.geotrellis.SpatialKey` are examples of this type of ``K``.
    """
    SPATIAL = 'spatial'

    """
    Indicates that the RDD contains ``(K, V)`` pairs, where the ``K`` has a spatial and
    time attribute. Both :class:`~geopyspark.geotrellis.TemporalProjectedExtent`
    and :class:`~geopyspark.geotrellis.SpaceTimeKey` are examples of this type of ``K``.
    """
    SPACETIME = 'spacetime'

    @classmethod
    def _from_key_name(cls, name):
        """Covnert GeoTrellis key class name into corresponding LayerType"""

        if name == "geotrellis.spark.SpatialKey" or name == "SpatialKey":
            return LayerType.SPATIAL
        elif name == "geotrellis.spark.SpaceTimeKey" or name == "SpaceTimeKey":
            return LayerType.SPACETIME
        elif name == "geotrellis.vector.ProjectedExtent" or name == "ProjectedExtent":
            return LayerType.SPATIAL
        elif name == "geotrellis.spark.TemporalProjectedExtent" or name == "TemporalProjectedExtent":
            return LayerType.SPACETIME
        else:
            raise ValueError("Unrecognized key class type: " + name)

    def _key_name(self, is_boundable):
        """Gets the mapped GeoTrellis type from the ``key_type``.

        Args:
            is_boundable (bool): Is ``K`` boundable.

        Returns:
            The corresponding GeoTrellis type.
        """

        if is_boundable:
            if self.value == "spatial":
                return "SpatialKey"
            elif self.value == "spacetime":
                return "SpaceTimeKey"
            else:
                raise Exception("Could not find key type that matches", self.value)
        else:
            if self.value == "spatial":
                return "ProjectedExtent"
            elif self.value == "spacetime":
                return "TemporalProjectedExtent"
            else:
                raise Exception("Could not find key type that matches", self.value)


class IndexingMethod(Enum):
    """How the wrapped should be indexed when saved."""

    """A key indexing method. Works for RDD that contain both :class:`~geopyspark.geotrellis.SpatialKey`
    and :class:`~geopyspark.geotrellis.SpaceTimeKey`.
    """
    ZORDER = 'zorder'

    """
    A key indexing method. Works for RDDs that contain both :class:`~geopyspark.geotrellis.SpatialKey`
    and :class:`~geopyspark.geotrellis.SpaceTimeKey`. Note, indexes are determined by the ``x``,
    ``y``, and if ``SPACETIME``, the temporal resolutions of a point. This is expressed in bits, and
    has a max value of 62. Thus if the sum of those resolutions are greater than 62,
    then the indexing will fail.
    """
    HILBERT = 'hilbert'

    """A key indexing method. Works only for RDDs that contain :class:`~geopyspark.geotrellis.SpatialKey`.
    This method provides the fastest lookup of all the key indexing method, however, it does not give
    good locality guarantees. It is recommended then that this method should only be used when locality
    is not important for your analysis.
    """
    ROWMAJOR = 'rowmajor'


class ResampleMethod(Enum):
    """Resampling Methods."""

    NEAREST_NEIGHBOR = 'NearestNeighbor'
    BILINEAR = 'Bilinear'
    CUBIC_CONVOLUTION = 'CubicConvolution'
    CUBIC_SPLINE = 'CubicSpline'
    LANCZOS = 'Lanczos'
    AVERAGE = 'Average'
    MODE = 'Mode'
    MEDIAN = 'Median'
    MAX = 'Max'
    MIN = 'Min'


class TimeUnit(Enum):
    """ZORDER time units."""

    MILLIS = 'millis'
    SECONDS = 'seconds'
    MINUTES = 'minutes'
    HOURS = 'hours'
    DAYS = 'days'
    WEEKS = 'weeks'
    MONTHS = 'months'
    YEARS = 'years'


class Operation(Enum):
    """Focal opertions."""

    SUM = 'Sum'
    MEAN = 'Mean'
    MODE = 'Mode'
    MEDIAN = 'Median'
    MAX = 'Max'
    MIN = 'Min'
    ASPECT = 'Aspect'
    VARIANCE = 'Variance'
    STANDARD_DEVIATION = 'StandardDeviation'


class Neighborhood(Enum):
    """Neighborhood types."""

    ANNULUS = 'Annulus'
    NESW = 'Nesw'
    SQUARE = 'Square'
    WEDGE = 'Wedge'
    CIRCLE = "Circle"


class ClassificationStrategy(Enum):
    """Classification strategies for color mapping."""

    GREATER_THAN = "GreaterThan"
    GREATER_THAN_OR_EQUAL_TO = "GreaterThanOrEqualTo"
    LESS_THAN = "LessThan"
    LESS_THAN_OR_EQUAL_TO = "LessThanOrEqualTo"
    EXACT = "Exact"


class CellType(Enum):
    """Cell types."""

    BOOLRAW = "boolraw"
    INT8RAW = "int8raw"
    UINT8RAW = "uint8raw"
    INT16RAW = "int16raw"
    UINT16RAW = "uint16raw"
    INT32RAW = "int32raw"
    FLOAT32RAW = "float32raw"
    FLOAT64RAW = "float64raw"
    BOOL = "bool"
    INT8 = "int8"
    UINT8 = "uint8"
    INT16 = "int16"
    UINT16 = "uint16"
    INT32 = "int32"
    FLOAT32 = "float32"
    FLOAT64 = "float64"

    @staticmethod
    def create_user_defined_celltype(cell_type, no_data_value):
        """This method is used when the user wishes to create a user defined, no data value
        for a given ``CellType``.

        Note:
            "bool" and "raw" ``CellType``\s cannot be create with user defined no data values.

        Args:
            cell_type (str or :class:`~geopyspark.geotrellis.constants.CellType`): The ``CellType``
                or its ``str`` representation.
            no_data_value: The custom no data value for the ``CellType``. Can be different types
                depending on the base ``CellType``.

        Returns:
            str: A ``str`` reprsentation of the ``CellType`` with the user's defined no data value.
        """

        cell_type = CellType(cell_type).value

        if 'bool' in cell_type:
            raise ValueError("Cannot add user defined types to Bool")
        elif 'raw' in cell_type:
            raise ValueError("Cannot add user defined types to raw values")

        return "{}{}{}".format(cell_type, "ud", no_data_value)


class ColorRamp(Enum):
    """ColorRamp names."""

    Hot = "Hot"
    COOLWARM = "CoolWarm"
    MAGMA = "Magma"
    INFERNO = "Inferno"
    PLASMA = "Plasma"
    VIRIDIS = "Viridis"
    BLUE_TO_ORANGE = "BlueToOrange"
    LIGHT_YELLOW_TO_ORANGE = "LightYellowToOrange"
    BLUE_TO_RED = "BlueToRed"
    GREEN_TO_RED_ORANGE = "GreenToRedOrange"
    LIGHT_TO_DARK_SUNSET = "LightToDarkSunset"
    LIGHT_TO_DARK_GREEN = "LightToDarkGreen"
    HEATMAP_YELLOW_TO_RED = "HeatmapYellowToRed"
    HEATMAP_BLUE_TO_YELLOW_TO_RED_SPECTRUM = "HeatmapBlueToYellowToRedSpectrum"
    HEATMAP_DARK_RED_TO_YELLOW_WHITE = "HeatmapDarkRedToYellowWhite"
    HEATMAP_LIGHT_PURPLE_TO_DARK_PURPLE_TO_WHITE = "HeatmapLightPurpleToDarkPurpleToWhite"
    CLASSIFICATION_BOLD_LAND_USE = "ClassificationBoldLandUse"
    CLASSIFICATION_MUTED_TERRAIN = "ClassificationMutedTerrain"


class StorageMethod(Enum):
    """Internal storage methods for GeoTiffs."""

    STRIPED = "Striped"
    TILED = "Tiled"


class ColorSpace(IntEnum):
    """Color space types for GeoTiffs."""

    WHITE_IS_ZERO = 0
    BLACK_IS_ZERO = 1
    RGB = 2
    PALETTE = 3
    TRANSPARENCY_MASK = 4
    CMYK = 5
    Y_CB_CR = 6
    CIE_LAB = 8
    ICC_LAB = 9
    ITU_LAB = 10
    CFA = 32803
    LINEAR_RAW = 34892
    LOG_L = 32844
    LOG_LUV = 32845


class Compression(Enum):
    """Compression methods for GeoTiffs."""

    NO_COMPRESSION = "NoCompression"
    DEFLATE_COMPRESSION = "DeflateCompression"


class Unit(Enum):
    """Represents the units of elevation."""

    METERS = "Meters"
    FEET = "Feet"
