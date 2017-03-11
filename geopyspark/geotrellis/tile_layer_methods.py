import json

from geopyspark.avroserializer import AvroSerializer


class TileLayerMethods(object):
    def __init__(self, geopysc):
        self.geopysc = geopysc

        self._metadata_wrapper = self.geopysc.tile_layer_metadata_collecter
        self._tiler_wrapper = self.geopysc.tile_layer_methods
        self._merge_wrapper = self.geopysc.tile_layer_merge

    @staticmethod
    def _map_outputs(key_type, value_type):
        if key_type == "spatial":
            key = "SpatialKey"
        else:
            key = "SpaceTimeKey"

        if value_type == "singleband":
            value = "Tile"
        else:
            value = "MultibandTile"

        return (key, value)

    def _convert_to_java_rdd(self, key_type, value_type, rdd):
        if isinstance(rdd._jrdd_deserializer.serializer, AvroSerializer):
            ser = rdd._jrdd_deserializer.serializer
            dumped = rdd.map(lambda value: ser.dumps(value))
            schema = rdd._jrdd_deserializer.serializer.schema_string
        else:
            ser = self.geopysc.create_serializer(key_type, value_type)
            reserialized_rdd = rdd._reserialize(ser)
            avro_ser = reserialized_rdd._jrdd_deserializer.serializer

            dumped = reserialized_rdd.map(lambda x: avro_ser.dumps(x))
            schema = reserialized_rdd._jrdd_deserializer.serializer.schema_string

        return (dumped._to_java_object_rdd(), schema)

    def collect_metadata(self,
                         key_type,
                         value_type,
                         rdd,
                         extent,
                         tile_layout,
                         proj_params=None,
                         epsg_code=None,
                         wkt_string=None):

        key = self.geopysc.map_key_input(key_type, False)
        value = self.geopysc.map_value_input(value_type)

        (java_rdd, schema) = self._convert_to_java_rdd(key, value, rdd)

        if proj_params:
            output_crs = {"projParams": proj_params}
        elif epsg_code:
            if isinstance(epsg_code, int):
                epsg_code = str(epsg_code)
                output_crs = {"epsg": epsg_code}
            elif wkt_string:
                output_crs = {"wktString": wkt_string}
            else:
                output_crs = {}

        metadata = self._metadata_wrapper.collectPythonMetadata(key_type,
                                                                value_type,
                                                                java_rdd.rdd(),
                                                                schema,
                                                                extent,
                                                                tile_layout,
                                                                output_crs)

        return json.loads(metadata)

    def cut_tiles(self,
                  key_type,
                  value_type,
                  rdd,
                  tile_layer_metadata,
                  resample_method=None):

        key = self.geopysc.map_key_input(key_type, False)
        value = self.geopysc.map_value_input(value_type)

        (java_rdd, schema) = self._convert_to_java_rdd(key, value, rdd)

        if resample_method is None:
            resample_dict = {}
        else:
            resample_dict = {"resampleMethod": resample_method}

        result = self._tiler_wrapper.cutTiles(key_type,
                                              value_type,
                                              java_rdd.rdd(),
                                              schema,
                                              json.dumps(tile_layer_metadata),
                                              resample_dict)

        (out_key, out_value) = self._map_outputs(key_type, value_type)

        return self.geopysc.avro_rdd_to_python(out_key,
                                               out_value,
                                               result._1(),
                                               result._2())

    def tile_to_layout(self,
                       key_type,
                       value_type,
                       rdd,
                       tile_layer_metadata,
                       resample_method=None):

        key = self.geopysc.map_key_input(key_type, False)
        value = self.geopysc.map_value_input(value_type)

        (java_rdd, schema) = self._convert_to_java_rdd(key, value, rdd)

        if resample_method is None:
            resample_dict = {}
        else:
            resample_dict = {"resampleMethod": resample_method}

        result = self._tiler_wrapper.tileToLayout(key_type,
                                                  value_type,
                                                  java_rdd.rdd(),
                                                  schema,
                                                  json.dumps(tile_layer_metadata),
                                                  resample_dict)

        (out_key, out_value) = self._map_outputs(key_type, value_type)

        return self.geopysc.avro_rdd_to_python(out_key,
                                               out_value,
                                               result._1(),
                                               result._2())

    def merge(self,
              key_type,
              value_type,
              rdd_1,
              rdd_2):

        key = self.geopysc.map_key_input(key_type, False)
        value = self.geopysc.map_value_input(value_type)

        (java_rdd_1, schema_1) = self._convert_to_java_rdd(key, value, rdd_1)
        (java_rdd_2, schema_2) = self._convert_to_java_rdd(key, value, rdd_2)

        result = self._merge_wrapper.merge(key_type,
                                           value_type,
                                           java_rdd_1.rdd(),
                                           schema_1,
                                           java_rdd_2.rdd(),
                                           schema_2)

        return self.geopysc.avro_rdd_to_python(key,
                                               value,
                                               result._1(),
                                               result._2())
