package geopyspark.util

import geotrellis.raster._

import org.apache.spark.rdd.RDD
import org.apache.spark.api.java.JavaRDD

import scala.reflect.ClassTag

import com.trueaccord.scalapb.GeneratedMessage


object PythonTranslator {
  def toPython[T, M <: GeneratedMessage](
    rdd: RDD[T]
  )(implicit codec: ProtoBufCodec[T, M]): JavaRDD[Array[Byte]] = {
    val result = rdd.map { v => codec.encode(v).toByteArray }.toJavaRDD
    result
  }

  def toPython[T, M <: GeneratedMessage](tile: T)(implicit codec: ProtoBufCodec[T, M]): Array[Byte] =
    codec.encode(tile).toByteArray

  def toPython[T, M <: GeneratedMessage](
    values: Seq[T]
  )(implicit codec: ProtoBufCodec[T, M]): java.util.ArrayList[Array[Byte]] = {
    val array_list: java.util.ArrayList[Array[Byte]] = new java.util.ArrayList()

   values
      .map({ v => codec.encode(v).toByteArray })
      .foreach({ ar => array_list.add(ar) })

    array_list
  }

  def fromPython[T: ClassTag, M <: GeneratedMessage](
    rdd: RDD[Array[Byte]],
    toProtoClass: Array[Byte] => M
  )(implicit codec: ProtoBufCodec[T, M]): RDD[T] =
    rdd.map { bytes => codec.decode(toProtoClass(bytes)) }
}
