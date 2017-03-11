package geopyspark.geotrellis.io

import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.spark.io.accumulo._
import geotrellis.spark.io.cassandra._
import geotrellis.spark.io.file._
import geotrellis.spark.io.hadoop._
import geotrellis.spark.io.hbase._
import geotrellis.spark.io.json._
import geotrellis.spark.io.s3._

import spray.json._

import org.apache.accumulo.core.client.security.tokens.PasswordToken
import org.apache.spark._


/**
  * Base wrapper class for various types of attribute store wrappers.
  */
abstract class AttributeStoreWrapper {
  def attributeStore: AttributeStore

  def header(name: String, zoom: Int): Array[String]

  def metadataSpatial(name: String, zoom: Int): String = {
    val id = LayerId(name, zoom)
    val md = attributeStore.readMetadata[TileLayerMetadata[SpatialKey]](id)
    md.toJson.compactPrint
  }

  def metadataSpaceTime(name: String, zoom: Int): String = {
    val id = LayerId(name, zoom)
    val md = attributeStore.readMetadata[TileLayerMetadata[SpaceTimeKey]](id)
    md.toJson.compactPrint
  }
}

/**
  * Accumulo wrapper.
  */
class AccumuloAttributeStoreWrapper(
  _instance: AccumuloInstance,
  attributeTable: String
) extends AttributeStoreWrapper {

  val attributeStore = AccumuloAttributeStore(_instance, attributeTable)

  def instance = _instance

  def table: String = attributeTable

  def header(name: String, zoom: Int): Array[String] = {
    val h = attributeStore.readHeader[CassandraLayerHeader](LayerId(name, zoom))
    Array[String](h.keyClass, h.valueClass, h.format, h.tileTable)
  }
}

/**
  * HBase wrapper.
  */
class HBaseAttributeStoreWrapper(
  instance: HBaseInstance,
  attributeTable: String
) extends AttributeStoreWrapper {

  val attributeStore = HBaseAttributeStore(instance, attributeTable)

  def table: String = attributeTable

  def header(name: String, zoom: Int): Array[String] = {
    val h = attributeStore.readHeader[CassandraLayerHeader](LayerId(name, zoom))
    Array[String](h.keyClass, h.valueClass, h.format, h.tileTable)
  }
}

/**
  * CassandraAttributeStore wrapper.
  */
class CassandraAttributeStoreWrapper(
  instance: CassandraInstance,
  attributeKeySpace: String,
  attributeTable: String
) extends AttributeStoreWrapper {

  val attributeStore = CassandraAttributeStore(instance, attributeKeySpace, attributeTable)

  def keySpace: String = attributeKeySpace

  def table: String = attributeTable

  def header(name: String, zoom: Int): Array[String] = {
    val h = attributeStore.readHeader[CassandraLayerHeader](LayerId(name, zoom))
    Array[String](h.keyClass, h.valueClass, h.keyspace, h.tileTable)
  }
}

/**
  * FileAttributeStore wrapper.
  *
  * @param  path  The local-filesystem location of the catalog
  */
class FileAttributeStoreWrapper(path: String)
    extends AttributeStoreWrapper {

  val attributeStore = FileAttributeStore(path)

  def header(name: String, zoom: Int): Array[String] = {
    val h = attributeStore.readHeader[FileLayerHeader](LayerId(name, zoom))
    Array[String](h.keyClass, h.valueClass, h.path)
  }
}

/**
  * S3AttributeStore wrapper.
  *
  * @param  bucket  The name of the S3 bucket
  * @param  root    The location of the layer within the bucket
  */
class S3AttributeStoreWrapper(bucket: String, root: String)
    extends AttributeStoreWrapper {

  val attributeStore = S3AttributeStore(bucket, root)

  def header(name: String, zoom: Int): Array[String] = {
    val h = attributeStore.readHeader[S3LayerHeader](LayerId(name, zoom))
    Array[String](h.keyClass, h.valueClass, h.bucket, h.key)
  }
}

/**
  * HadoopAttributeStore wrapper.
  *
  * @param  uri  The URI where the catalog is located
  * @param  sc   The SparkContext
  */
class HadoopAttributeStoreWrapper(uri: String, sc: SparkContext)
    extends AttributeStoreWrapper {

  val sparkContext = sc
  val attributeStore = HadoopAttributeStore(uri)(sparkContext)

  def header(name: String, zoom: Int): Array[String] = {
    val h = attributeStore.readHeader[HadoopLayerHeader](LayerId(name, zoom))
    Array[String](h.keyClass, h.valueClass, h.path.toString)
  }
}

/**
  * Interface for requesting attribute store wrappers.  This object is
  * easily accessible from PySpark.
  */
object AttributeStoreFactory {

  def buildHadoop(uri: String, sc: SparkContext): AttributeStoreWrapper =
    new HadoopAttributeStoreWrapper(uri, sc)

  def buildS3(bucket: String, root: String): AttributeStoreWrapper =
    new S3AttributeStoreWrapper(bucket, root)

  def buildFile(path: String): AttributeStoreWrapper =
    new FileAttributeStoreWrapper(path)

  def buildCassandra(
    hosts: String,
    username: String,
    password: String,
    replicationStrategy: String,
    replicationFactor: Int,
    localDc: String,
    usedHostsPerRemoteDc: Int,
    allowRemoteDCsForLocalConsistencyLevel: Int,
    attributeKeySpace: String,
    attributeTable: String
  ) = {
    val instance = BaseCassandraInstance(
      hosts.split(","),
      username,
      password,
      if (replicationStrategy != "") replicationStrategy; else Cassandra.cfg.getString("replicationStrategy"),
      if (replicationFactor > -1) replicationFactor; else Cassandra.cfg.getInt("replicationFactor"),
      if (localDc != "") localDc; else Cassandra.cfg.getString("localDc"),
      if (usedHostsPerRemoteDc > -1) usedHostsPerRemoteDc; else Cassandra.cfg.getInt("usedHostsPerRemoteDc"),
      allowRemoteDCsForLocalConsistencyLevel match {
        case 1 => true
        case 0 => false
        case _ => Cassandra.cfg.getBoolean("allowRemoteDCsForLocalConsistencyLevel")
      })
    new CassandraAttributeStoreWrapper(
      instance,
      if (attributeKeySpace != "") attributeKeySpace; else Cassandra.cfg.getString("keyspace"),
      if (attributeTable != "") attributeTable; else Cassandra.cfg.getString("catalog")
    )
  }

  def buildHBase(
    zookeepers: String,
    master: String,
    clientPort: String,
    attributeTable: String
  ) = {
    val instance = HBaseInstance(
      zookeepers.split(","),
      master,
      clientPort
    )
    new HBaseAttributeStoreWrapper(instance, attributeTable)
  }

  def buildAccumulo(
    zookeepers: String,
    instanceName: String,
    user: String,
    password: String,
    attributeTable: String
  ) = {
    val instance = AccumuloInstance(
      instanceName,
      zookeepers,
      user,
      new PasswordToken(password)
    )
    new AccumuloAttributeStoreWrapper(instance, attributeTable)
  }
}
