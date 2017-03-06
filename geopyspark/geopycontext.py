from geopyspark.avroregistry import AvroRegistry

from pyspark import SparkContext
from py4j.java_gateway import java_import


class GeoPyContext(object):
    def __init__(self, pysc, avroregistry=None):
        self.pysc = pysc
        self.sc = self.pysc._jsc.sc()
        self._jvm = self.pysc._gateway.jvm

        if avroregistry:
            self.avroregistry = avroregistry
        else:
            aself.avroregistry = AvroRegistry()

    @staticmethod
    def construct(*args, **kwargs):
        return GeoPyContext(SparkContext(*args, **kwargs))

    @property
    def schema_producer(self):
        return self._jvm.geopyspark.geotrellis.SchemaProducer

    @property
    def hadoop_geotiff_rdd(self):
        return self._jvm.geopyspark.geotrellis.io.hadoop.HadoopGeoTiffRDDWrapper

    @property
    def s3_geotiff_rdd(self):
        return self._jvm.geopyspark.geotrellis.io.s3.S3GeoTiffRDDWrapper

    @property
    def store_factory(self):
        return self._jvm.geopyspark.geotrellis.io.AttributeStoreFactory

    @property
    def reader_factory(self):
        return self._jvm.geopyspark.geotrellis.io.LayerReaderFactory

    @property
    def writer_factory(self):
        return self._jvm.geopyspark.geotrellis.io.LayerWriterFactory

    @property
    def tile_layer_metadata_collecter(self):
        return self._jvm.geopyspark.geotrellis.spark.TileLayerMetadataCollector

    @property
    def tile_layer_methods(self):
        return self._jvm.geopyspark.geotrellis.spark.tiling.TilerMethodsWrapper

    @property
    def tile_layer_merge(self):
        return self._jvm.geopyspark.geotrellis.spark.merge.MergeMethodsWrapper

    def produce_schema(key_type, value_type):
        return self.schema_producer.getSchema(key_type, value_type)

    def stop(self):
        self.pysc.stop()

    def close_gateway(self):
        self.pysc._gateway.close()
