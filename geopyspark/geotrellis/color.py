from geopyspark.geopyspark_utils import check_environment
check_environment()

from geopyspark.geotrellis.constants import RESAMPLE_METHODS, NEARESTNEIGHBOR, ZOOM, COLOR_RAMPS, LESSTHANOREQUALTO

import struct

def get_breaks_from_colors(colors):
    """Returns a list of integer colors from a list of Color objects from the
    colortools package.

    Args:
        colors ([Color]): A list of color stops using colortools.Color

    Returns:
        [int]
    """
    return [struct.unpack(">L", bytes(c.rgba))[0] for c in colors]

def get_breaks_from_matplot(ramp_name, num_colors):
    """Returns a list of color breaks from the color ramps defined by Matplotlib.

    Args:
        ramp_name (str): The name of a matplotlib color ramp; options are
            'viridis', 'plasma', 'inferno', 'magma', 'Greys', 'Purples', 'Blues',
            'Greens', 'Oranges', 'Reds', 'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd',
            'RdPu', 'BuPu', 'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn',
            'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink', 'spring',
            'summer', 'autumn', 'winter', 'cool', 'Wistia', 'hot', 'afmhot',
            'gist_heat', 'copper', 'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
            'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic',
            'Pastel1', 'Pastel2', 'Paired', 'Accent', 'Dark2', 'Set1', 'Set2',
            'Set3', 'tab10', 'tab20', 'tab20b', 'tab20c', 'flag', 'prism',
            'ocean', 'gist_earth', 'terrain', 'gist_stern', 'gnuplot',
            'gnuplot2', 'CMRmap', 'cubehelix', 'brg', 'hsv', 'gist_rainbow',
            'rainbow', 'jet', 'nipy_spectral', 'gist_ncar'.  See the matplotlib
            documentation for details on each color ramp.
        num_colors (int): The number of color breaks to derive from the named map.

    Returns:
        [int]
    """
    import colortools
    import matplotlib.cm as mpc
    ramp = mpc.get_cmap(ramp_name)
    return  [ struct.unpack('>L', bytes(map(lambda x: int(x*255), ramp(x / (num_colors - 1)))))[0] for x in range(0, num_colors)]

def get_breaks(pysc, ramp_name, num_colors=None):
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
        return list(pysc._gateway.jvm.geopyspark.geotrellis.ColorRampUtils.get(ramp_name, num_colors))
    else:
        return list(pysc._gateway.jvm.geopyspark.geotrellis.ColorRampUtils.get(ramp_name))

def get_hex(pysc, ramp_name, num_colors=None):
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
        return list(pysc._gateway.jvm.geopyspark.geotrellis.ColorRampUtils.getHex(ramp_name, num_colors))
    else:
        return list(pysc._gateway.jvm.geopyspark.geotrellis.ColorRampUtils.getHex(ramp_name))

"""A dict giving the color mapping from NLCD values to colors
"""
nlcd_color_map =  { 0  : 0x00000000,
                    11 : 0x526095FF,     # Open Water
                    12 : 0xFFFFFFFF,     # Perennial Ice/Snow
                    21 : 0xD28170FF,     # Low Intensity Residential
                    22 : 0xEE0006FF,     # High Intensity Residential
                    23 : 0x990009FF,     # Commercial/Industrial/Transportation
                    31 : 0xBFB8B1FF,     # Bare Rock/Sand/Clay
                    32 : 0x969798FF,     # Quarries/Strip Mines/Gravel Pits
                    33 : 0x382959FF,     # Transitional
                    41 : 0x579D57FF,     # Deciduous Forest
                    42 : 0x2A6B3DFF,     # Evergreen Forest
                    43 : 0xA6BF7BFF,     # Mixed Forest
                    51 : 0xBAA65CFF,     # Shrubland
                    61 : 0x45511FFF,     # Orchards/Vineyards/Other
                    71 : 0xD0CFAAFF,     # Grasslands/Herbaceous
                    81 : 0xCCC82FFF,     # Pasture/Hay
                    82 : 0x9D5D1DFF,     # Row Crops
                    83 : 0xCD9747FF,     # Small Grains
                    84 : 0xA7AB9FFF,     # Fallow
                    85 : 0xE68A2AFF,     # Urban/Recreational Grasses
                    91 : 0xB6D8F5FF,     # Woody Wetlands
                    92 : 0xB6D8F5FF }    # Emergent Herbaceous Wetlands

class ColorMap(object):
    """A class to represent a color map
    """
    def __init__(self, cmap):
        self.cmap = cmap

    @classmethod
    def from_break_map(cls, pysc, break_map, no_data_color=0x00000000, fallback=0x00000000, class_boundary_type=LESSTHANOREQUALTO):
        """Converts a dictionary mapping from tile values to colors to a ColorMap.

        Args:
            pysc (pyspark.context.SparkContext): The ``SparkContext`` being used this session.
            break_map (dict): A mapping from tile values to colors, the latter
                represented as integers---e.g., 0xff000080 is red at half opacity.
            no_data_color(int, optional): A color to replace NODATA values with
            fallback (int, optional): A color to replace cells that have no
                value in the mapping
            class_boundary_type (string, optional): A string giving the strategy
                for converting tile values to colors.  E.g., if
                LESSTHANOREQUALTO is specified, and the break map is
                {3: 0xff0000ff, 4: 0x00ff00ff}, then values up to 3 map to red,
                values from above 3 and up to and including 4 become green, and
                values over 4 become the fallback color.

        Returns:
            [ColorMap]
        """
        if all(isinstance(x, int) for x in break_map.keys()):
            return cls(pysc._gateway.jvm.geopyspark.geotrellis.ColorMapUtils.fromMap(break_map, no_data_color, fallback, class_boundary_type))
        elif all(isinstance(x, float) for x in break_map.keys()):
            return cls(pysc._gateway.jvm.geopyspark.geotrellis.ColorMapUtils.fromMapDouble(break_map, no_data_color, fallback, class_boundary_type))
        else:
            raise TypeError("Break map keys must be either int or float.")

    @classmethod
    def from_colors(cls, pysc, breaks, color_list, no_data_color=0x00000000, fallback=0x00000000, class_boundary_type=LESSTHANOREQUALTO):
        """Converts lists of values and colors to a ColorMap.

        Args:
            pysc (pyspark.context.SparkContext): The ``SparkContext`` being used this session.
            breaks (list): The tile values that specify breaks in the color
                mapping
            color_list (int list): The colors corresponding to the values in the
                breaks list, represented as integers---e.g., 0xff000080 is red
                at half opacity.
            no_data_color(int, optional): A color to replace NODATA values with
            fallback (int, optional): A color to replace cells that have no
                value in the mapping
            class_boundary_type (string, optional): A string giving the strategy
                for converting tile values to colors.  E.g., if
                LESSTHANOREQUALTO is specified, and the break map is
                {3: 0xff0000ff, 4: 0x00ff00ff}, then values up to 3 map to red,
                values from above 3 and up to and including 4 become green, and
                values over 4 become the fallback color.

        Returns:
            [ColorMap]
        """
        if all(isinstance(x, int) for x in breaks):
            return cls(pysc._gateway.jvm.geopyspark.geotrellis.ColorMapUtils.fromBreaks(breaks, color_list, no_data_color, fallback, class_boundary_type))
        else:
            return cls(pysc._gateway.jvm.geopyspark.geotrellis.ColorMapUtils.fromBreaksDouble([float(br) for br in breaks], color_list, no_data_color, fallback, class_boundary_type))

    @classmethod
    def from_histogram(cls, pysc, histogram, color_list, no_data_color=0x00000000, fallback=0x00000000, class_boundary_type=LESSTHANOREQUALTO):
        return cls(pysc._gateway.jvm.geopyspark.geotrellis.ColorMapUtils.fromHistogram(histogram, color_list, no_data_color, fallback, class_boundary_type))

    @staticmethod
    def nlcd_colormap(pysc):
        """Returns a color map for NLCD tiles.

        Args:
            pysc (pyspark.context.SparkContext): The ``SparkContext`` being used this session.

        Returns:
            [ColorMap]
        """
        return ColorMap.from_break_map(pysc, nlcd_color_map)
