package geopyspark.geotrellis

import geotrellis.spark.io._
import geotrellis.spark.io.avro._
import geotrellis.spark.util.KryoWrapper

import org.apache.spark._
import org.apache.spark.rdd.RDD
import org.apache.spark.api.java.JavaRDD
import org.apache.avro._

import scala.reflect.ClassTag

object PythonTranslator {
  def toPython[T: AvroRecordCodec](rdd: RDD[T]): (JavaRDD[Array[Byte]], String) = {
    val jrdd =
      rdd
        .map { v =>
          AvroEncoder.toBinary(v, deflate = false)
        }
        .toJavaRDD
    (jrdd, implicitly[AvroRecordCodec[T]].schema.toString)
  }

  def toPython[T : AvroRecordCodec](tile: T): (Array[Byte], String) = {
    val data = AvroEncoder.toBinary(tile, deflate = false)
    val schema = implicitly[AvroRecordCodec[T]].schema.toString

    (data, schema)
  }

  def fromPython[T: AvroRecordCodec: ClassTag]
  (rdd: RDD[Array[Byte]], schemaJson: Option[String] = None): RDD[T] = {
    val schema = schemaJson.map { json => (new Schema.Parser).parse(json) }
    val _recordCodec = implicitly[AvroRecordCodec[T]]
    val kwWriterSchema = KryoWrapper(schema)

    rdd.map { bytes =>
      AvroEncoder
        .fromBinary(kwWriterSchema.value.getOrElse(_recordCodec.schema), bytes, false)(_recordCodec)
    }
  }
}
