import json

from shapely.geometry import Polygon
from shapely.wkt import dumps


class _Catalog(object):

    def __init__(self, geopysc):
        self.geopysc = geopysc

        self.store = None
        self.reader = None
        self.writer = None

    def _read(self,
              key_type,
              value_type,
              layer_name,
              layer_zoom):

        key = self.geopysc.map_key_input(key_type, True)
        value = self.geopysc.map_value_input(value_type)

        tup = self.reader.read(key, value, layer_name, layer_zoom)
        schema = tup._2()

        if key_type == "spatial":
            jmetadata = self.store.metadataSpatial(layer_name, layer_zoom)
        else:
            jmetadata = self.store.metadataSpaceTime(layer_name, layer_zoom)

        metadata = json.loads(jmetadata)
        rdd = self.geopysc.avro_rdd_to_python(key, value, tup._1(), schema)

        return (rdd, schema, metadata)

    def _query(self,
               key_type,
               value_type,
               layer_name,
               layer_zoom,
               intersects,
               time_intervals):

        key = self.geopysc.map_key_input(key_type, True)
        value = self.geopysc.map_value_input(value_type)

        if time_intervals is None:
            time_intervals = []

        if isinstance(intersects, Polygon):
            tup = self.reader.query(key,
                                    value,
                                    layer_name,
                                    layer_zoom,
                                    dumps(intersects),
                                    time_intervals)

        elif isinstance(intersects, str):
            tup = self.reader.query(key,
                                    value,
                                    layer_name,
                                    layer_zoom,
                                    intersects,
                                    time_intervals)
        else:
            raise Exception("Could not query intersection", intersects)

        schema = tup._2()

        if key_type == "spatial":
            jmetadata = self.store.metadataSpatial(layer_name, layer_zoom)
        else:
            jmetadata = self.store.metadataSpaceTime(layer_name, layer_zoom)

        metadata = json.loads(jmetadata)
        rdd = self.geopysc.avro_rdd_to_python(key, value, tup._1(), schema)

        return (rdd, schema, metadata)

    def _write(self,
               key_type,
               value_type,
               layer_name,
               layer_zoom,
               rdd,
               metadata,
               time_unit,
               index_strategy):

        key = self.geopysc.map_key_input(key_type, True)
        value = self.geopysc.map_value_input(value_type)

        schema = metadata.schema

        if not time_unit:
            time_unit = ""

        self.writer.write(key,
                          value,
                          layer_name,
                          layer_zoom,
                          rdd._jrdd,
                          json.dumps(metadata),
                          schema,
                          time_unit,
                          index_strategy)


class HadoopCatalog(_Catalog):

    __slots__ = ["geopysc",
                 "store",
                 "reader",
                 "writer",
                 "uri"]

    def __init__(self, geopysc):

        super().__init__(geopysc)
        self.geopysc = geopysc

        self.uri = None

    def _construct_catalog(self, new_uri):
        if new_uri != self.uri and new_uri is not None:
            self.uri = new_uri

            self.store = self.geopysc.store_factory.buildHadoop(self.uri)

            self.reader = \
                    self.geopysc.reader_factory.buildHadoop(self.store,
                                                            self.geopysc.sc)
            self.writer = \
                    self.geopysc.writer_factory.buildHadoop(self.store)

    def read(self,
             key_type,
             value_type,
             uri,
             layer_name,
             layer_zoom):

        self._construct_catalog(uri)

        return self._read(key_type,
                          value_type,
                          layer_name,
                          layer_zoom)
    def query(self,
              key_type,
              value_type,
              uri,
              layer_name,
              layer_zoom,
              intersects,
              time_intervals=None):

        self._construct_catalog(uri)

        return self._query(key_type,
                           value_type,
                           layer_name,
                           layer_zoom,
                           intersects,
                           time_intervals)

    def write(self,
              key_type,
              value_type,
              layer_name,
              layer_zoom,
              rdd,
              metadata,
              index_strategy="zorder",
              time_unit=None,
              uri=None):

        if uri is not None:
            self._construct_catalog(uri)

        self._write(key_type,
                    value_type,
                    layer_name,
                    layer_zoom,
                    rdd,
                    metadata,
                    time_unit,
                    index_strategy)


class S3Catalog(_Catalog):

    __slots__ = ["geopysc",
                 "store",
                 "reader",
                 "writer",
                 "bucket",
                 "prefix"]

    def __init__(self, geopysc):

        super().__init__(geopysc)
        self.geopysc = geopysc

        self.bucket = None
        self.prefix = None

    def _construct_catalog(self, new_bucket, new_prefix):
        bucket = new_bucket != self.bucket and new_bucket is not None
        prefix = new_prefix != self.prefix and new_prefix is not None

        if bucket or prefix:
            self.bucket = new_bucket
            self.prefix = new_prefix

            self.store = self.geopysc.store_factory.buildS3(self.bucket,
                                                            self.prefix)

            self.reader = \
                    self.geopysc.reader_factory.buildS3(self.store,
                                                        self.geopysc.sc)

            self.writer = self.geopysc.writer_factory.buildS3(self.store)

    def read(self,
             key_type,
             value_type,
             bucket,
             prefix,
             layer_name,
             layer_zoom):

        self._construct_catalog(bucket, prefix)

        return self._read(key_type,
                          value_type,
                          layer_name,
                          layer_zoom)
    def query(self,
              key_type,
              value_type,
              bucket,
              prefix,
              layer_name,
              layer_zoom,
              intersects,
              time_intervals=None):

        self._construct_catalog(bucket, prefix)

        return self._query(key_type,
                           value_type,
                           layer_name,
                           layer_zoom,
                           intersects,
                           time_intervals)

    def write(self,
              key_type,
              value_type,
              layer_name,
              layer_zoom,
              rdd,
              metadata,
              index_strategy="zorder",
              time_unit=None,
              bucket=None,
              prefix=None):

        if bucket is not None or prefix is not None:
            self._construct_catalog(bucket, prefix)

        self._write(key_type,
                    value_type,
                    layer_name,
                    layer_zoom,
                    rdd,
                    metadata,
                    time_unit,
                    index_strategy)


class FileCatalog(_Catalog):

    __slots__ = ["geopysc",
                 "store",
                 "reader",
                 "writer",
                 "path"]

    def __init__(self, geopysc):

        super().__init__(geopysc)
        self.geopysc = geopysc
        self.path = None

    def _construct_catalog(self, new_path):
        if new_path != self.path and new_path is not None:
            self.path = new_path

            self.store = self.geopysc.store_factory.buildFile(self.path)

            self.reader = \
                    self.geopysc.reader_factory.buildFile(self.store,
                                                          self.geopysc.sc)
            self.writer = \
                    self.geopysc.writer_factory.buildFile(self.store)

    def read(self,
             key_type,
             value_type,
             path,
             layer_name,
             layer_zoom):

        self._construct_catalog(path)

        return self._read(key_type,
                          value_type,
                          layer_name,
                          layer_zoom)

    def query(self,
              key_type,
              value_type,
              path,
              layer_name,
              layer_zoom,
              intersects,
              time_intervals=None):

        self._construct_catalog(path)

        return self._query(key_type,
                           value_type,
                           layer_name,
                           layer_zoom,
                           intersects,
                           time_intervals)

    def write(self,
              key_type,
              value_type,
              layer_name,
              layer_zoom,
              rdd,
              metadata,
              time_unit=None,
              index_strategy="zorder",
              path=None):

        if path is not None:
            self._construct_catalog(path)

        self._write(key_type,
                    value_type,
                    layer_name,
                    layer_zoom,
                    rdd,
                    metadata,
                    time_unit,
                    index_strategy)


class CassandraCatalog(_Catalog):

    __slots__ = ["geopysc",
                 "store",
                 "reader",
                 "writer",
                 "hosts",
                 "username",
                 "password",
                 "replication_strategy",
                 "replication_factor",
                 "local_dc",
                 "uhprd",
                 "allow_remote_dcs_for_lcl",
                 "attribute_key_space",
                 "attribute_table"]

    def __init__(self,
                 geopysc,
                 hosts,
                 username,
                 password,
                 replication_strategy,
                 replication_factor,
                 local_dc,
                 uhprd,
                 allow_remote_dcs_for_lcl):

        super().__init__(geopysc)
        self.geopysc = geopysc

        self.hosts = hosts
        self.username = username
        self.password = password
        self.replication_strategy = replication_strategy
        self.replication_factor = replication_factor
        self.local_dc = local_dc
        self.uhpd = uhprd
        self.allow_remote_dcs_for_lcl = allow_remote_dcs_for_lcl

        self.attribute_key_space = None
        self.attribute_table = None

    def _construct_catalog(self, new_attribute_key_space, new_attribute_table):
        is_old_key = new_attribute_key_space != self.attribute_key_space
        is_none_key = new_attribute_key_space is not None

        is_old_table = new_attribute_table != self.attribute_table
        is_none_table = new_attribute_table is not None

        if (is_old_key and is_none_key) or (is_old_table and is_none_table):
            self.attribute_key_space = new_attribute_key_space
            self.attribute_table = new_attribute_table

            self.store = self.geopysc.store_factory.buildCassandra(
                self.hosts,
                self.username,
                self.password,
                self.replication_strategy,
                self.replication_factor,
                self.local_dc,
                self.uhpd,
                self.allow_remote_dcs_for_lcl,
                self.attribute_key_space,
                self.attribute_table)

            self.reader = \
                    self.geopysc.reader_factory.buildCassandra(self.store,
                                                               self.geopysc.sc)

            self.writer = \
                    self.geopysc.writer_factory.buildCassandra(self.store,
                                                               self.attribute_key_space,
                                                               self.attribute_table)

    def read(self,
             key_type,
             value_type,
             attribute_key_space,
             attribute_table,
             layer_name,
             layer_zoom):

        self._construct_catalog(attribute_key_space, attribute_table)

        return self._read(key_type,
                          value_type,
                          layer_name,
                          layer_zoom)

    def query(self,
              key_type,
              value_type,
              attribute_key_space,
              attribute_table,
              layer_name,
              layer_zoom,
              intersects,
              time_intervals=None):

        self._construct_catalog(attribute_key_space, attribute_table)

        return self._query(key_type,
                           value_type,
                           layer_name,
                           layer_zoom,
                           intersects,
                           time_intervals)

    def write(self,
              key_type,
              value_type,
              layer_name,
              layer_zoom,
              rdd,
              metadata,
              time_unit=None,
              index_strategy="zorder",
              attribute_key_space=None,
              attribute_table=None):

        if attribute_key_space is not None or attribute_table is not None:
            self._construct_catalog(attribute_key_space, attribute_table)

        self._write(key_type,
                    value_type,
                    layer_name,
                    layer_zoom,
                    rdd,
                    metadata,
                    time_unit,
                    index_strategy)


class HBaseCatalog(_Catalog):

    __slots__ = ["geopysc",
                 "store",
                 "reader",
                 "writer",
                 "zookeepers",
                 "master",
                 "client_port",
                 "attribute_table"]

    def __init__(self,
                 geopysc,
                 zookeepers,
                 master,
                 client_port):

        super().__init__(geopysc)
        self.geopysc = geopysc

        self.zookeepers = zookeepers
        self.master = master
        self.client_port = client_port

        self.attribute_table = None

    def _construct_catalog(self, new_attribute_table):
        is_old = new_attribute_table != self.attribute_table
        is_none = new_attribute_table is not None

        if is_old and is_none:
            self.attribute_table = new_attribute_table
            self.store = \
                    self.geopysc.store_factory.buildHBase(self.zookeepers,
                                                          self.master,
                                                          self.client_port,
                                                          self.attribute_table)
            self.reader = \
                    self.geopysc.reader_factory.buildHBase(self.store,
                                                           self.geopysc.sc)

            self.writer = \
                    self.geopysc.writer_factory.buildHBase(self.store,
                                                           self.attribute_table)


    def read(self,
             key_type,
             value_type,
             attribute_table,
             layer_name,
             layer_zoom):

        self._construct_catalog(attribute_table)

        return self._read(key_type,
                          value_type,
                          layer_name,
                          layer_zoom)

    def query(self,
              key_type,
              value_type,
              attribute_table,
              layer_name,
              layer_zoom,
              intersects,
              time_intervals=None):

        self._construct_catalog(attribute_table)

        return self._query(key_type,
                           value_type,
                           layer_name,
                           layer_zoom,
                           intersects,
                           time_intervals)

    def write(self,
              key_type,
              value_type,
              layer_name,
              layer_zoom,
              rdd, metadata,
              time_unit=None,
              index_strategy="zorder",
              attribute_table=None):

        if attribute_table is not None:
            self._construct_catalog(attribute_table)

        self._write(key_type,
                    value_type,
                    layer_name,
                    layer_zoom,
                    rdd,
                    metadata,
                    time_unit,
                    index_strategy)


class AccumuloCatalog(_Catalog):

    __slots__ = ["geopysc",
                 "store",
                 "reader",
                 "writer",
                 "zookeepers",
                 "instance_name",
                 "user",
                 "password",
                 "attribute_table"]

    def __init__(self,
                 geopysc,
                 zookeepers,
                 instance_name,
                 user,
                 password):

        super().__init__(geopysc)
        self.geopysc = geopysc

        self.zookeepers = zookeepers
        self.instance_name = instance_name
        self.user = user
        self.password = password

        self.attribute_table = None

    def _construct_catalog(self, new_attribute_table):
        is_old = new_attribute_table != self.attribute_table
        is_none = new_attribute_table is not None

        if is_old and is_none:
            self.attribute_table = new_attribute_table
            self.store = \
                    self.geopysc.store_factory.buildAccumulo(self.zookeepers,
                                                             self.instance_name,
                                                             self.user,
                                                             self.password,
                                                             self.attribute_table)
            self.reader = \
                    self.geopysc.reader_factory.buildAccumulo(self.instance_name,
                                                              self.store,
                                                              self.geopysc.sc)
            self.writer = \
                    self.geopysc.writer_factory.buildAccumulo(self.instance_name,
                                                              self.store,
                                                              self.attribute_table)

    def read(self,
             key_type,
             value_type,
             attribute_table,
             layer_name,
             layer_zoom):

        self._construct_catalog(attribute_table)

        return self._read(key_type,
                          value_type,
                          layer_name,
                          layer_zoom)

    def query(self,
              key_type,
              value_type,
              attribute_table,
              layer_name,
              layer_zoom,
              intersects,
              time_intervals=None):

        self._construct_catalog(attribute_table)

        return self._query(key_type,
                           value_type,
                           layer_name,
                           layer_zoom,
                           intersects,
                           time_intervals)

    def write(self,
              key_type,
              value_type,
              layer_name,
              layer_zoom,
              rdd,
              metadata,
              time_unit=None,
              index_strategy="zorder",
              attribute_table=None):

        if attribute_table is not None:
            self._construct_catalog(attribute_table)

        self._write(key_type,
                    value_type,
                    layer_name,
                    layer_zoom,
                    rdd,
                    metadata,
                    time_unit,
                    index_strategy)
