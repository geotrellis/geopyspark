import shapely.wkb
from geopyspark.geotrellis.constants import LayerType, CellType
from geopyspark.geotrellis.layer import TiledRasterLayer


__all__ = ['rasterize']


def rasterize(pysc, geoms, crs, zoom, fill_value, cell_type=CellType.FLOAT64, options=None, num_partitions=None):
    """Rasterizes a Shapely geometries.

    Args:
        pysc (pyspark.SparkContext): The ``SparkContext`` being used this session.
        geoms ([shapely.geometry]): List of shapely geometries to rasterize.
        crs (str or int): The CRS of the input geometry.
        zoom (int): The zoom level of the output raster.
        fill_value (int or float): Value to burn into pixels intersectiong geometry
        cell_type (str or :class:`~geopyspark.geotrellis.constants.CellType`): Which data type the
            cells should be when created. Defaults to ``CellType.FLOAT64``.
        options (:class:`~geopyspark.geotrellis.RasterizerOptions`): Pixel intersection options.

    Returns:
        :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
    """

    if isinstance(crs, int):
        crs = str(crs)

    wkb_geoms = [shapely.wkb.dumps(g) for g in geoms]
    srdd = pysc._gateway.jvm.geopyspark.geotrellis.SpatialTiledRasterLayer.rasterizeGeometry(pysc._jsc.sc(),
                                                                                             wkb_geoms,
                                                                                             crs,
                                                                                             zoom, float(fill_value),
                                                                                             CellType(cell_type).value,
                                                                                             options,
                                                                                             num_partitions)
    return TiledRasterLayer(pysc, LayerType.SPATIAL, srdd)
