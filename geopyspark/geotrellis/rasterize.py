from shapely.wkb import dumps
from geopyspark import get_spark_context
from geopyspark.geotrellis.constants import LayerType, CellType
from geopyspark.geotrellis.layer import TiledRasterLayer
from geopyspark.geotrellis.protobufserializer import ProtoBufSerializer

from geopyspark.vector_pipe.vector_pipe_protobufcodecs import (feature_cellvalue_decoder,
                                                               feature_cellvalue_encoder)


__all__ = ['rasterize', 'rasterize_features']


def rasterize(geoms, crs, zoom, fill_value, cell_type=CellType.FLOAT64, options=None, num_partitions=None):
    """Rasterizes a Shapely geometries.

    Args:
        geoms ([shapely.geometry] or (shapely.geometry) or pyspark.RDD[shapely.geometry]): Either
            a list, tuple, or a Python RDD of shapely geometries to rasterize.
        crs (str or int): The CRS of the input geometry.
        zoom (int): The zoom level of the output raster.
        fill_value (int or float): Value to burn into pixels intersectiong geometry
        cell_type (str or :class:`~geopyspark.geotrellis.constants.CellType`): Which data type the
            cells should be when created. Defaults to ``CellType.FLOAT64``.
        options (:class:`~geopyspark.geotrellis.RasterizerOptions`, optional): Pixel intersection options.
        num_partitions (int, optional): The number of repartitions Spark will make when the data is
            repartitioned. If ``None``, then the data will not be repartitioned.

    Returns:
        :class:`~geopyspark.geotrellis.layer.TiledRasterLayer`
    """

    if isinstance(crs, int):
        crs = str(crs)

    pysc = get_spark_context()
    rasterizer = pysc._gateway.jvm.geopyspark.geotrellis.SpatialTiledRasterLayer.rasterizeGeometry

    if isinstance(geoms, (list, tuple)):
        wkb_geoms = [dumps(g) for g in geoms]

        srdd = rasterizer(pysc._jsc.sc(),
                          wkb_geoms,
                          crs,
                          zoom,
                          float(fill_value),
                          CellType(cell_type).value,
                          options,
                          num_partitions)

    else:
        wkb_rdd = geoms.map(lambda geom: dumps(geom))

        # If this is False then the WKBs will be serialized
        # when going to Scala resulting in garbage
        wkb_rdd._bypass_serializer = True

        srdd = rasterizer(wkb_rdd._jrdd.rdd(),
                          crs,
                          zoom,
                          float(fill_value),
                          CellType(cell_type).value,
                          options,
                          num_partitions)

    return TiledRasterLayer(LayerType.SPATIAL, srdd)


def rasterize_features(features,
                       crs,
                       zoom,
                       cell_type=CellType.FLOAT64,
                       options=None,
                       num_partitions=None,
                       zindex_cell_type=CellType.INT8):

    if isinstance(crs, int):
        crs = str(crs)

    pysc = get_spark_context()
    rasterizer = pysc._gateway.jvm.geopyspark.geotrellis.SpatialTiledRasterLayer.rasterizeFeaturesWithZIndex

    ser = ProtoBufSerializer(feature_cellvalue_decoder, feature_cellvalue_encoder)
    reserialized_rdd = features._reserialize(ser)

    srdd = rasterizer(reserialized_rdd._jrdd.rdd(),
                      crs,
                      zoom,
                      CellType(cell_type).value,
                      options,
                      num_partitions,
                      CellType(zindex_cell_type).value)

    return TiledRasterLayer(LayerType.SPATIAL, srdd)
