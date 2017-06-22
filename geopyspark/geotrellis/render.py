from geopyspark.geopyspark_utils import check_environment
check_environment()

from geopyspark.geotrellis.constants import RESAMPLE_METHODS, NEARESTNEIGHBOR, ZOOM, COLOR_RAMPS
from .rdd import CachableRDD
from pyspark.storagelevel import StorageLevel
import geopyspark.geotrellis.color as color
from geopyspark.geotrellis import deprecated

@deprecated
def get_breaks_from_colors(colors):
    """Deprecated in favor of geopyspark.geotrellis.color.get_breaks_from_colors
    """
    return color.get_breaks_from_colors(colors)

@deprecated
def get_breaks_from_matplot(ramp_name, num_colors):
    """Deprecated in favor of geopyspark.geotrellis.color.get_breaks_from_matplot
    """
    return color.get_breaks_from_matplot(ramp_name, num_colors)

@deprecated
def get_breaks(pysc, ramp_name, num_colors=None):
    """Deprecated in favor of geopyspark.geotrellis.color.get_breaks
    """
    return color.get_breaks(pysc, ramp_name, num_colors=None)

@deprecated
def get_hex(pysc, ramp_name, num_colors=None):
    """Deprecated in favor of geopyspark.geotrellis.color.get_hex
    """
    return color.get_hex(pysc, ramp_name, num_colors=None)


# What does this do? implements lookup method ... this is a wrapper, a delegator
class PngRDD(CachableRDD):
    def __init__(self, pyramid, color_map, debug=False):
        """Convert a pyramid of TiledRasterRDDs into a displayable structure of PNGs

        Args:
            pyramid (list): A pyramid of TiledRasterRDD resulting from calling the pyramid
                method on an instance of that class
            color_map (JavaObject): Mapping from cell values to cell colors
        """

        level0 = pyramid[0]
        self.pysc = level0.pysc
        self.rdd_type = level0.rdd_type
        self.layer_metadata = dict([(lev.zoom_level, lev.layer_metadata) for lev in pyramid])
        self.max_zoom = level0.zoom_level
        if level0.is_floating_point_layer():
            self.pngpyramid = dict([(layer.zoom_level, self.pysc._gateway.jvm.geopyspark.geotrellis.PngRDD.asSingleband(layer.srdd, color_map)) for layer in pyramid])
        else:
            self.pngpyramid = dict([(layer.zoom_level, self.pysc._gateway.jvm.geopyspark.geotrellis.PngRDD.asIntSingleband(layer.srdd, color_map)) for layer in pyramid])
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
        if resample_method not in RESAMPLE_METHODS:
            raise ValueError(resample_method, " Is not a known resample method.")

        reprojected = tiledrdd.reproject("EPSG:3857", scheme=ZOOM)

        if not start_zoom:
            if reprojected.zoom_level:
                start_zoom = reprojected.zoom_level
            else:
                raise AttributeError("No initial zoom level is available; Please provide a value for start_zoom")

        pyramid = reprojected.pyramid(start_zoom, end_zoom, resample_method)

        return cls(pyramid, ramp_name, debug)

    def lookup(self, col, row, zoom=None):
        """Return the value(s) in the image of a particular SpatialKey (given by col and row)

        Args:
            col (int): The SpatialKey column
            row (int): The SpatialKey row

        Returns: A list of bytes containing the resulting PNG images
        """

        pngrdd = self.pngpyramid[zoom]
        metadata = self.layer_metadata[zoom]

        bounds = metadata.bounds
        min_col = bounds.minKey.col
        min_row = bounds.minKey.row
        max_col = bounds.maxKey.col
        max_row = bounds.maxKey.row

        if col < min_col or col > max_col:
            raise IndexError("column out of bounds")
        if row < min_row or row > max_row:
            raise IndexError("row out of bounds")

        result = pngrdd.lookup(col, row)

        return [bytes for bytes in result]

    def wrapped_rdds(self):
        return iter(self.pngpyramid.values())
