package geopyspark.geotrellis.spark.tiling

import geopyspark.geotrellis._
import geopyspark.geotrellis.GeoTrellisUtils._

import geotrellis.util._
import geotrellis.proj4._
import geotrellis.vector._
import geotrellis.raster._
import geotrellis.raster.merge._
import geotrellis.raster.prototype._
import geotrellis.raster.resample._
import geotrellis.spark._
import geotrellis.spark.io.avro._
import geotrellis.spark.tiling._

import org.apache.spark._
import org.apache.spark.rdd._
import org.apache.spark.api.java.JavaRDD

import scala.collection.JavaConverters._
import collection.JavaConversions._
import java.util.Map

import scala.reflect.ClassTag


object TilerMethodsWrapper {
  private def getMetadata[
  K: GetComponent[?, ProjectedExtent]: (? => TilerKeyMethods[K, K2]): AvroRecordCodec: ClassTag,
  V <: CellGrid: AvroRecordCodec: ClassTag,
  K2: Boundable: SpatialComponent
  ](
    returnedRdd: RDD[Array[Byte]],
    schema: String,
    pythonTileDefinition: java.util.List[java.util.Map[String, _]],
    pythonCRS: String
  ): (RDD[(K, V)], TileLayerMetadata[K2]) = {
    val rdd: RDD[(K, V)] = PythonTranslator.fromPython[(K, V)](returnedRdd, Some(schema))
    val layoutDefinition: LayoutDefinition = pythonTileDefinition.toLayoutDefinition
    val crs: CRS = CRS.fromString(pythonCRS)

    (rdd, rdd.collectMetadata[K2](crs, layoutDefinition))
  }

  // TODO: Refactor this code so that the tileToLayout is performed via the
  // cutTiles method.

  def cutTiles(
    keyType: String,
    valueType: String,
    returnedRdd: RDD[Array[Byte]],
    schema: String,
    pythonTileDefinition: java.util.List[java.util.Map[String, _]],
    pythonCRS: String,
    resampleMap: java.util.Map[String, String]
  ): (JavaRDD[Array[Byte]], String) = {
    val resampleMethod =
      if (resampleMap.isEmpty)
        TilerOptions.default.resampleMethod
      else
        TilerOptions.getResampleMethod(Some(resampleMap("resampleMethod")))

    (keyType, valueType) match {
      case ("spatial", "singleband") =>
        val (rdd, metadata) =
          getMetadata[ProjectedExtent, Tile, SpatialKey](
            returnedRdd,
            schema,
            pythonTileDefinition,
            pythonCRS)

        val result = rdd.cutTiles(metadata, resampleMethod)

        PythonTranslator.toPython(result)

      case ("spatial", "multiband") =>
        val (rdd, metadata) =
          getMetadata[ProjectedExtent, MultibandTile, SpatialKey](
            returnedRdd,
            schema,
            pythonTileDefinition,
            pythonCRS)

        val result = rdd.cutTiles(metadata, resampleMethod)

        PythonTranslator.toPython(result)

      case ("spacetime", "singleband") =>
        val (rdd, metadata) =
          getMetadata[TemporalProjectedExtent, Tile, SpaceTimeKey](
            returnedRdd,
            schema,
            pythonTileDefinition,
            pythonCRS)

        val result = rdd.cutTiles(metadata, resampleMethod)

        PythonTranslator.toPython(result)

      case ("spacetime", "multiband") =>
        val (rdd, metadata) =
          getMetadata[TemporalProjectedExtent, MultibandTile, SpaceTimeKey](
            returnedRdd,
            schema,
            pythonTileDefinition,
            pythonCRS)

        val result = rdd.cutTiles(metadata, resampleMethod)

        PythonTranslator.toPython(result)
    }
  }

  def tileToLayout(
    keyType: String,
    valueType: String,
    returnedRdd: RDD[Array[Byte]],
    schema: String,
    pythonTileDefinition: java.util.List[java.util.Map[String, _]],
    pythonCRS: String,
    options: java.util.Map[String, Any]
  ): (JavaRDD[Array[Byte]], String) = {
    val returnedOptions =
      if (options.isEmpty)
        TilerOptions.default
      else
        TilerOptions.setValues(options)

    (keyType, valueType) match {
      case ("spatial", "singleband") =>
        val (rdd, metadata) =
          getMetadata[ProjectedExtent, Tile, SpatialKey](
            returnedRdd,
            schema,
            pythonTileDefinition,
            pythonCRS)

        val result = rdd.tileToLayout(metadata, returnedOptions)

        PythonTranslator.toPython(result)

      case ("spatial", "multiband") =>
        val (rdd, metadata) =
          getMetadata[ProjectedExtent, MultibandTile, SpatialKey](
            returnedRdd,
            schema,
            pythonTileDefinition,
            pythonCRS)

        val result = rdd.tileToLayout(metadata, returnedOptions)

        PythonTranslator.toPython(result)

      case ("spacetime", "singleband") =>
        val (rdd, metadata) =
          getMetadata[TemporalProjectedExtent, Tile, SpaceTimeKey](
            returnedRdd,
            schema,
            pythonTileDefinition,
            pythonCRS)

        val result = rdd.tileToLayout(metadata, returnedOptions)

        PythonTranslator.toPython(result)

      case ("spacetime", "multiband") =>
        val (rdd, metadata) =
          getMetadata[TemporalProjectedExtent, MultibandTile, SpaceTimeKey](
            returnedRdd,
            schema,
            pythonTileDefinition,
            pythonCRS)

        val result = rdd.tileToLayout(metadata, returnedOptions)

        PythonTranslator.toPython(result)
    }
  }
}
