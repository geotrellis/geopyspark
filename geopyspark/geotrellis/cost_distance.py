import shapely.wkb
from geopyspark.geotrellis.layer import TiledRasterLayer


def cost_distance(friction_layer, geometries, max_distance):
    """Performs cost distance of a TileLayer.

    Args:
        friction_layer(:class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`):
            Tiled raster of a friction surface to traverse.
        geometries (list):
            A list of shapely geometries to be used as a starting point.

            Note:
                All geometries must be in the same CRS as the TileLayer.
        max_distance (int, float): The maximum cost that a path may reach before the operation.
            stops. This value can be an ``int`` or ``float``.

    Returns:
        :class:`~geopyspark.geotrellis.rdd.TiledRasterLayer`
    """

    wkbs = [shapely.wkb.dumps(g) for g in geometries]
    srdd = friction_layer.srdd.costDistance(
        friction_layer.pysc._jsc.sc(),
        wkbs,
        float(max_distance))

    return TiledRasterLayer(friction_layer.pysc, friction_layer.rdd_type, srdd)
