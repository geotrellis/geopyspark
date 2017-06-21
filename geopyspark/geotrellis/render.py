from geopyspark.geopyspark_utils import check_environment
check_environment()

from geopyspark.geotrellis.constants import RESAMPLE_METHODS, NEARESTNEIGHBOR, ZOOM, COLOR_RAMPS
from .rdd import CachableRDD
from pyspark.storagelevel import StorageLevel


def get_breaks(geopysc, ramp_name, num_colors=None):
    """Returns a list of values that represent the breaks in color for the given color ramp.

    Args:
        ramp_name (str): The name of a color ramp; options are hot, COOLWARM, MAGMA,
            INFERNO, PLASMA, VIRIDIS, BLUETOORANGE, LIGHTYELLOWTOORANGE, BLUETORED,
            GREENTOREDORANGE, LIGHTTODARKSUNSET, LIGHTTODARKGREEN, HEATMAPYELLOWTORED,
            HEATMAPBLUETOYELLOWTOREDSPECTRUM, HEATMAPDARKREDTOYELLOWWHITE,
            HEATMAPLIGHTPURPLETODARKPURPLETOWHITE, CLASSIFICATIONBOLDLANDUSE, and
            CLASSIFICATIONMUTEDTERRAIN
        num_colors (int, optional): How many colors should be represented in the range. Defaults
            to ``None``. If not specified, then the full range of values will be returned.

    Returns:
        [int]
    """

    if num_colors:
        return list(geopysc._jvm.geopyspark.geotrellis.ColorRamp.get(ramp_name, num_colors))
    else:
        return list(geopysc._jvm.geopyspark.geotrellis.ColorRamp.get(ramp_name))

def get_hex(geopysc, ramp_name, num_colors=None):
    """Returns a list of the hex values that represent the colors for the given color ramp.

    Note:
        The returning hex values contain an alpha value.

    Args:
        ramp_name (str): The name of a color ramp; options are HOT, COOLWARM, MAGMA,
            INFERNO, PLASMA, VIRIDIS, BLUETOORANGE, LIGHTYELLOWTOORANGE, BLUETORED,
            GREENTOREDORANGE, LIGHTTODARKSUNSET, LIGHTTODARKGREEN, HEATMAPYELLOWTORED,
            HEATMAPBLUETOYELLOWTOREDSPECTRUM, HEATMAPDARKREDTOYELLOWWHITE,
            HEATMAPLIGHTPURPLETODARKPURPLETOWHITE, CLASSIFICATIONBOLDLANDUSE, and
            CLASSIFICATIONMUTEDTERRAIN
        num_colors (int, optional): How many colors should be represented in the range. Defaults
            to ``None``. If not specified, then the full range of values will be returned.

    Returns:
        [str]
    """

    if num_colors:
        return list(geopysc._jvm.geopyspark.geotrellis.ColorRamp.getHex(ramp_name, num_colors))
    else:
        return list(geopysc._jvm.geopyspark.geotrellis.ColorRamp.getHex(ramp_name))


class PngRDD(CachableRDD):
    def __init__(self, pyramid, ramp_name, debug=False):
        """Convert a pyramid of TiledRasterRDDs into a displayable structure of PNGs

        Args:
            pyramid (list): A pyramid of TiledRasterRDD resulting from calling the pyramid
                method on an instance of that class
            ramp_name (str): The name of a color ramp; This is represented by the following
                constants; HOT, COOLWARM, MAGMA, INFERNO, PLASMA, VIRIDIS, BLUE_TO_ORANGE,
                LIGHT_YELLOW_TO_ORANGE, BLUE_TO_RED, GREEN_TO_RED_ORANGE, LIGHT_TO_DARK_SUNSET,
                LIGHT_TO_DARK_GREEN, HEATMAP_YELLOW_TO_RED, HEATMAP_BLUE_TO_YELLOW_TO_RED_SPECTRUM,
                HEATMAP_DARK_RED_TO_YELLOW_WHITE, HEATMAP_LIGHT_PURPLE_TO_DARK_PURPLE_TO_WHITE,
                CLASSIFICATION_BOLD_LAND_USE, and CLASSIFICATION_MUTED_TERRAIN
        """

        __slots__ = ['geopysc', 'rdd_type', 'layer_metadata', 'max_zoom', 'pngpyramid', 'debug']

        if ramp_name not in COLOR_RAMPS:
            raise ValueError(ramp_name, "Is not a known color ramp")

        level0 = pyramid[0]
        self.geopysc = level0.geopysc
        self.rdd_type = level0.rdd_type
        self.layer_metadata = list(map(lambda lev: lev.layer_metadata, pyramid))
        self.max_zoom = level0.zoom_level
        histogram = level0.get_histogram()
        if level0.is_floating_point_layer():
            self.pngpyramid = [self.geopysc._jvm.geopyspark.geotrellis.PngRDD.asSingleband(layer.srdd, histogram, ramp_name) for layer in pyramid]
        else:
            self.pngpyramid = [self.geopysc._jvm.geopyspark.geotrellis.PngRDD.asIntSingleband(layer.srdd, histogram, ramp_name) for layer in pyramid]
        self.debug = debug
        self.is_cached = False

    @classmethod
    def makePyramid(cls, tiledrdd, ramp_name, start_zoom=None, end_zoom=0, resample_method=NEARESTNEIGHBOR, debug=False):
        """Create a pyramided PngRDD from a TiledRasterRDD

        Args:
            tiledrdd (TiledRasterRDD): The TiledRasterRDD source
            ramp_name (str): The name of a color ramp; This is represented by the following
                constants; HOT, COOLWARM, MAGMA, INFERNO, PLASMA, VIRIDIS, BLUE_TO_ORANGE,
                LIGHT_YELLOW_TO_ORANGE, BLUE_TO_RED, GREEN_TO_RED_ORANGE, LIGHT_TO_DARK_SUNSET,
                LIGHT_TO_DARK_GREEN, HEATMAP_YELLOW_TO_RED, HEATMAP_BLUE_TO_YELLOW_TO_RED_SPECTRUM,
                HEATMAP_DARK_RED_TO_YELLOW_WHITE, HEATMAP_LIGHT_PURPLE_TO_DARK_PURPLE_TO_WHITE,
                CLASSIFICATION_BOLD_LAND_USE, and CLASSIFICATION_MUTED_TERRAIN
            start_zoom (int, optional): The starting (highest resolution) zoom level for
                the pyramid.  Defaults to the zoom level of the source RDD.
            end_zoom (int, optional): The final (lowest resolution) zoom level for the
                pyramid.  Defaults to 0.
            resample_method (str, optional): The resample method to use for the reprojection.
                This is represented by a constant. If none is specified, then NEARESTNEIGHBOR
                is used.

        Returns: A PngRDD object
        """
        if not start_zoom:
            start_zoom = tiledrdd.zoom_level
            if not start_zoom:
                raise AttributeError("No initial zoom level is available; Please provide a value for start_zoom")

        pyramid = tiledrdd.pyramid(start_zoom, end_zoom, resample_method)

        return cls(pyramid, ramp_name, debug)

    def lookup(self, col, row, zoom=None):
        """Return the value(s) in the image of a particular SpatialKey (given by col and row)

        Args:
            col (int): The SpatialKey column
            row (int): The SpatialKey row

        Returns: A list of bytes containing the resulting PNG images
        """
        if not zoom:
            idx = 0
        else:
            idx = self.max_zoom - zoom

        pngrdd = self.pngpyramid[idx]
        metadata = self.layer_metadata[idx]

        bounds = metadata.bounds
        min_col = bounds.minKey['col']
        min_row = bounds.minKey['row']
        max_col = bounds.maxKey['col']
        max_row = bounds.maxKey['row']

        if col < min_col or col > max_col:
            raise IndexError("column out of bounds")
        if row < min_row or row > max_row:
            raise IndexError("row out of bounds")

        result = pngrdd.lookup(col, row)

        return [bytes for bytes in result]

    def wrapped_rdds(self):
        return self.pngpyramid

