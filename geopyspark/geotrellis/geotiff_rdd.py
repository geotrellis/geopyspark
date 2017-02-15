from geopyspark.geotrellis import decode_java_rdd
from py4j.java_gateway import java_import


class HadoopGeoTiffRDD(object):
    def __init__(self, pysc, avroregistry=None):

        self.pysc = pysc
        self.avroregistry = avroregistry

        self._sc = self.pysc._jsc.sc()

        java_import(self.pysc._gateway.jvm,
                "geopyspark.geotrellis.io.hadoop.HadoopGeoTiffRDDWrapper")

        self._hadoop_wrapper = self.pysc._gateway.jvm.HadoopGeoTiffRDDWrapper

    def get_spatial(self, path, options=None):
        if options is None:
            result = self._hadoop_wrapper.readSpatialSingleband(path, self._sc)
        else:
            result = self._hadoop_wrapper.readSpatialSingleband(path, options, self._sc)

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)

    def get_spatial_multiband(self, path, options=None):
        if options is None:
            result = self._hadoop_wrapper.readSpatialMultiband(path, self._sc)
        else:
            result = self._hadoop_wrapper.readSpatialMultiband(path, options, self._sc)

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)

    def get_spacetime(self, path, options=None):
        if options is None:
            result = self._hadoop_wrapper.readSpaceTimeSingleband(path, self._sc)
        else:
            result = self._hadoop_wrapper.readSpaceTimeSingleband(path, options, self._sc)

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)

    def get_spacetime_multiband(self, path, options=None):
        if options is None:
            result = self._hadoop_wrapper.readSpaceTimeMultiband(path, self._sc)
        else:
            result = self._hadoop_wrapper.readSpaceTimeMultiband(path, options, self._sc)

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)


class S3GeoTiffRDD(object):
    def __init__(self, pysc, avroregistry=None):

        self.pysc = pysc
        self.avroregistry = avroregistry

        self._sc = self.pysc._jsc.sc()

        java_import(self.pysc._gateway.jvm,
                "geopyspark.geotrellis.io.s3.S3GeoTiffRDDWrapper")

        self._s3_wrapper = self.pysc._gateway.jvm.S3GeoTiffRDDWrapper

    def get_spatial(self, bucket, prefix, options=None):
        if options is None:
            result = self._s3_wrapper.readSpatialSingleband(bucket, prefix, self._sc)
        else:
            result = self._s3_wrapper.readSpatialSingleband(bucket, prefix, options, self._sc)

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)

    def get_spatial_multiband(self, bucket, prefix, options=None):
        if options is None:
            result = self._s3_wrapper.readSpatialMultiband(bucket, prefix, self._sc)
        else:
            result = self._s3_wrapper.readSpatialMultiband(bucket, prefix, options, self._sc)

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)

    def get_spacetime(self, bucket, prefix, options=None):
        if options is None:
            result = self._s3_wrapper.readSpaceTimeSingleband(bucket, prefix, self._sc)
        else:
            result = self._s3_wrapper.readSpaceTimeSingleband(bucket, prefix, options, self._sc)

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)

    def get_spacetime_multiband(self, bucket, prefix, options=None):
        if options is None:
            result = self._s3_wrapper.readSpaceTimeMultiband(bucket, prefix, self._sc)
        else:
            result = self._s3_wrapper.readSpaceTimeMultiband(bucket, prefix, options, self._sc)

        return decode_java_rdd(self.pysc, result._1(), result._2(), self.avroregistry)
