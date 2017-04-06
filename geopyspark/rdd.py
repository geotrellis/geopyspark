import json

from geopyspark.constants import RESAMPLE_METHODS, NEARESTNEIGHBOR, ZOOM, FLOAT


class RasterRDD(object):
    """Holds an RDD of GeoTrellis rasters"""

    def __init__(self, geopysc, rdd_type, srdd):
        self.geopysc = geopysc
        self.rdd_type = rdd_type
        self.srdd = srdd

    def to_numpy_rdd(self):
        result = self.srdd.toAvroRDD()
        ser = self.geopysc.create_tuple_serializer(result._2(), value_type="Tile")
        return self.geopysc.create_python_rdd(result._1(), ser)

    '''
    @static
    def from_numpy_rdd(numpy_rdd):
        pass
    '''

    def collect_metadata(self, crs=None, extent=None, layout=None, tile_size=256):
        """Iterate over RDD records and generate layer metadata desribing the contained rasters.

        Keyword arguments:
        crs -- Ignore CRS from records and use given
        extent -- Specify layout extent, must also specify layout
        layout -- Specify tile layout, must also specify layout
        tile_size -- Pixel dimensions of each tile, if not using layout
        """

        ret = self.srdd.collect_metadata(crs, json.dumps(extent), json.dumps(layout), tile_size)
        return json.loads(ret)

    def reproject(self, target_crs, resample_method=NEARESTNEIGHBOR):
        """Reproject every individual raster to target_crs, does not sample past tile boundary"""
        return RasterRDD(self.geopysc, self.rdd_type,
                         self.srdd.reproject(target_crs, resample_method))

    def cut_tiles(self, layerMetadata, resample_method=NEARESTNEIGHBOR, cellType=None):
        """Cut tiles to layout. May result in duplicate keys"""
        assert(resample_method in RESAMPLE_METHODS)
        srdd = self.srdd.cutTiles(json.dumps(layerMetadata), resample_method)
        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def tile_to_layout(self, layerMetadata, resample_method=NEARESTNEIGHBOR):
        """Cut tiles to layout and merge overlapping tiles. This will produce unique keys"""
        assert(resample_method in RESAMPLE_METHODS)
        srdd = self.srdd.tileToLayout(json.dumps(layerMetadata), resample_method)
        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)


class TiledRasterRDD(object):
    """Holds an RDD of GeoTrellis tile layer"""

    def __init__(self, geopysc, rdd_type, srdd):
        self.geopysc = geopysc
        self.rdd_type = rdd_type
        self.srdd = srdd

    @property
    def layer_metadata(self):
        """Layer metadata associated with this layer"""
        return json.loads(self.srdd.layerMetadata())

    @property
    def zoom_level(self):
        zoom = self.srdd.getZoom()

        if zoom >= 0:
            return zoom
        else:
            raise AttributeError("Tile layer does not have a corresponding zoom level")

    def to_numpy_rdd(self):
        result = self.srdd.toAvroRDD()
        ser = self.geopysc.create_tuple_serializer(result._2(), value_type="Tile")
        return self.geopysc.create_python_rdd(result._1(), ser)

    def reproject(self, target_crs, scheme=FLOAT, tile_size=256, resample_method=NEARESTNEIGHBOR,
                  resolution_threshold=0.1, extent=None, layout=None):
        """Reproject RDD as tiled raster layer, samples surrounding tiles
        `extent` and `layout` may be specified if `scheme` is FLOAT
        """
        srdd = self.srdd.reproject(target_crs, scheme, tile_size, resample_method,
                                     resolution_threshold, extent, layout)
        return TiledRasterRDD(self.geopysc, self.rdd_type, srdd)

    def tile_to_layout(self, layout):
        pass

    def pyramid(self, start_zoom, end_zoom, resample_method):
        pass

    def focal(self):
        pass
