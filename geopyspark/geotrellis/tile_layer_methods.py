from py4j.java_gateway import java_import
from geopyspark.avroserializer import AvroSerializer
from geopyspark.singleton_base import SingletonBase
from geopyspark.geotrellis import decode_java_rdd

import json


class TileLayerMethods(metaclass=SingletonBase):
    def __init__(self, pysc, avroregistry=None):
        self.pysc = pysc
        self.avroregistry = avroregistry

        _tiler_path = "geopyspark.geotrellis.spark.tiling.TilerMethodsWrapper"
        _metadata_path = "geopyspark.geotrellis.spark.TileLayerMetadataCollector"

        java_import(self.pysc._gateway.jvm, _tiler_path)
        java_import(self.pysc._gateway.jvm, _metadata_path)

        self._metadata_wrapper = self.pysc._gateway.jvm.TileLayerMetadataCollector
        self._tiler_wrapper = self.pysc._gateway.jvm.TilerMethodsWrapper

    @staticmethod
    def _get_key_value_types(schema):
        schema_json = json.loads(schema)

        key = schema_json['fields'][0]['type']['name']
        value = schema_json['fields'][1]['type'][0]['name']

        if key == "ProjectedExtent":
            key_type = "spatial"
        else:
            key_type = "spacetime"

        if value != "ArrayMultibandTile":
            value_type = "singleband"
        else:
            value_type = "multiband"

        return (key_type, value_type)

    @classmethod
    def _get_tiling_parameters(cls, schema, resample_method):
        types = cls._get_key_value_types(schema)

        if resample_method is None:
            resample_dict = {}
        else:
            resample_dict = {"resampleMethod": resample_method}

        return (types, resample_dict)

    def _convert_to_java_rdd(self, rdd, schema):
        ser = AvroSerializer(schema, self.avroregistry)
        dumped = rdd.map(lambda value: ser.dumps(value, schema))

        return dumped._to_java_object_rdd()

    def collect_metadata(self,
                         rdd,
                         schema,
                         extent,
                         tile_layout,
                         proj_params=None,
                         epsg_code=None,
                         wkt_string=None):

        types = self._get_key_value_types(schema)

        if proj_params:
            crs = {"projParams": proj_params}

        elif epsg_code:
            if isinstance(epsg_code, int):
                epsg_code = str(epsg_code)

            crs = {"epsg": epsg_code}

        elif wkt_string:
            crs = {"wktString": wkt_string}

        else:
            return {}

        java_rdd = self._convert_to_java_rdd(rdd, schema)

        return self._metadata_wrapper.collectPythonMetadata(types[0],
                                                            types[1],
                                                            java_rdd.rdd(),
                                                            schema,
                                                            extent,
                                                            tile_layout,
                                                            crs)

    def cut_tiles(self,
                  rdd,
                  schema,
                  tile_layer_metadata,
                  resample_method=None):

        java_rdd = self._convert_to_java_rdd(rdd, schema)
        params = self._get_tiling_parameters(schema, resample_method)

        result = self._tiler_wrapper.cutTiles(params[0][0],
                                              params[0][1],
                                              java_rdd.rdd(),
                                              schema,
                                              tile_layer_metadata['layout'],
                                              tile_layer_metadata['crs'],
                                              params[1])

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)

    def tile_to_layout(self,
                  rdd,
                  schema,
                  tile_layer_metadata,
                  resample_method=None):

        java_rdd = self._convert_to_java_rdd(rdd, schema)
        params = self._get_tiling_parameters(schema, resample_method)

        result = self._tiler_wrapper.tileToLayout(params[0][0],
                                              params[0][1],
                                              java_rdd.rdd(),
                                              schema,
                                              tile_layer_metadata['layout'],
                                              tile_layer_metadata['crs'],
                                              params[1])

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)
