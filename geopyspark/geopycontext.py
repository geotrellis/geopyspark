from geopyspark.avroregistry import AvroRegistry
from geopyspark.avroserializer import AvroSerializer

from pyspark import RDD, SparkContext
from pyspark.serializers import AutoBatchedSerializer


class GeoPyContext(object):
    def __init__(self, pysc=None, **kwargs):
        if pysc:
            self.pysc = pysc
        elif kwargs:
            self.pysc = SparkContext(**kwargs)
        else:
            raise TypeError(("Either a SparkContext or its constructing"
                             " parameters must be given,"
                             " but none were found"))

        self.sc = self.pysc._jsc.sc()
        self._jvm = self.pysc._gateway.jvm

        self.avroregistry = AvroRegistry()

    @property
    def _schema_producer(self):
        return self._jvm.geopyspark.geotrellis.SchemaProducer

    @property
    def _hadoop_geotiff_rdd(self):
        return self._jvm.geopyspark.geotrellis.io.hadoop.HadoopGeoTiffRDDWrapper

    @property
    def _s3_geotiff_rdd(self):
        return self._jvm.geopyspark.geotrellis.io.s3.S3GeoTiffRDDWrapper

    @property
    def _store_factory(self):
        return self._jvm.geopyspark.geotrellis.io.AttributeStoreFactory

    @property
    def _reader_factory(self):
        return self._jvm.geopyspark.geotrellis.io.LayerReaderFactory

    @property
    def _value_reader_factory(self):
        return self._jvm.geopyspark.geotrellis.io.ValueReaderFactory

    @property
    def _writer_factory(self):
        return self._jvm.geopyspark.geotrellis.io.LayerWriterFactory

    @property
    def _tile_layer_metadata_collecter(self):
        return self._jvm.geopyspark.geotrellis.spark.TileLayerMetadataCollector

    @property
    def _tile_layer_methods(self):
        return self._jvm.geopyspark.geotrellis.spark.tiling.TilerMethodsWrapper

    @property
    def _tile_layer_merge(self):
        return self._jvm.geopyspark.geotrellis.spark.merge.MergeMethodsWrapper

    @property
    def _pyramid_builder(self):
        return self._jvm.geopyspark.geotrellis.spark.pyramid.PyramidWrapper

    @property
    def _rdd_reprojector(self):
        return self._jvm.geopyspark.geotrellis.spark.reproject.ReprojectWrapper

    @property
    def rdd_focal(self):
        return self._jvm.geopyspark.geotrellis.spark.focal.FocalWrapper

    @property
    def rdd_stitch(self):
        return self._jvm.geopyspark.geotrellis.spark.stitch.StitchWrapper

    @property
    def rdd_costdistance(self):
        return self._jvm.geopyspark.geotrellis.spark.costdistance.CostDistanceWrapper

    @property
    def _projected_raster_rdd(self):
        return self._jvm.geopyspark.geotrellis.ProjectedRasterRDD

    @property
    def _temporal_raster_rdd(self):
        return self._jvm.geopyspark.geotrellis.TemporalRasterRDD

    @staticmethod
    def map_key_input(key_type, is_boundable):
        if is_boundable:
            if key_type == "spatial":
                return "SpatialKey"
            elif key_type == "spacetime":
                return "SpaceTimeKey"
            else:
                raise Exception("Could not find key type that matches", key_type)
        else:
            if key_type == "spatial":
                return "ProjectedExtent"
            elif key_type == "spacetime":
                return "TemporalProjectedExtent"
            else:
                raise Exception("Could not find key type that matches", key_type)

    def create_schema(self, key_type):
        return self._schema_producer.getSchema(key_type)

    def create_tuple_serializer(self, schema, key_type=None, value_type=None):
        decoder = \
                self.avroregistry.create_partial_tuple_decoder(key_type=key_type,
                                                               value_type=value_type)

        encoder = \
                self.avroregistry.create_partial_tuple_encoder(key_type=key_type,
                                                               value_type=value_type)

        return AutoBatchedSerializer(AvroSerializer(schema, decoder, encoder))

    def create_value_serializer(self, schema, value_type):
        decoder = self.avroregistry.get_decoder(value_type)
        encoder = self.avroregistry.get_encoder(value_type)

        return AvroSerializer(schema, decoder, encoder)

    def create_python_rdd(self, jrdd, serializer):
        if isinstance(serializer, AutoBatchedSerializer):
            return RDD(jrdd, self.pysc, serializer)
        else:
            return RDD(jrdd, self.pysc, AutoBatchedSerializer(serializer))
