from geopyspark.geopycontext import GeoPyContext


class HadoopGeoTiffRDD(object):
    def __init__(self, geopysc):
        self.geopysc = geopysc
        self._hadoop_wrapper = self.geopysc.hadoop_geotiff_rdd

    def get_rdd(self, key_type, value_type, path, options=None):
        key = self.geopysc.map_key_input(key_type, False)
        value = self.geopysc.map_value_input(value_type)

        if options is None:
            result = self._hadoop_wrapper.getRDD(key, value, path, self.geopysc.sc)
        else:
            result = self._hadoop_wrapper.getRDD(key, value, path, options, self.geopysc.sc)

        return self.geopysc.avro_rdd_to_python(key, value, result._1(), result._2())


class S3GeoTiffRDD(object):
    def __init__(self, geopysc):
        self.geopysc = geopysc
        self._s3_wrapper = self.geopysc.s3_geotiff_rdd

    def get_rdd(self, key_type, value_type, bucket, prefix, options=None):
        key = self.geopysc.map_key_input(key_type, False)
        value = self.geopysc.map_value_input(value_type)

        if options is None:
            result = self._s3_wrapper.getRDD(key, value, bucket, prefix, self.geopysc.sc)
        else:
            result = self._s3_wrapper.getRDD(key, value, bucket, prefix, options, self.geopysc.sc)

        return self.geopysc.avro_rdd_to_python(key, value, result._1(), result._2())
