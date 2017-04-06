package geopyspark.geotrellis

import geotrellis.util._
import geotrellis.proj4._
import geotrellis.vector._
import geotrellis.vector.io._
import geotrellis.raster._
import geotrellis.raster.io._
import geotrellis.raster.merge._
import geotrellis.raster.prototype._
import geotrellis.raster.resample._
import geotrellis.spark._
import geotrellis.spark.reproject._
import geotrellis.spark.io._
import geotrellis.spark.io.json._
import geotrellis.spark.io.avro._
import geotrellis.spark.tiling._
import org.apache.spark.api.java.JavaRDD
import org.apache.spark.rdd._
import spray.json._
import spray.json.DefaultJsonProtocol._
import scala.reflect._

abstract class TiledRasterRDD[K: SpatialComponent: AvroRecordCodec: JsonFormat: ClassTag] extends TileRDD[K] {
  def rdd: RDD[(K, MultibandTile)] with Metadata[TileLayerMetadata[K]]
  def zoomLevel: Option[Int]

  def getZoom: Int =
    zoomLevel match {
      case None => -1
      case Some(z) => z
    }

  /** Encode RDD as Avro bytes and return it with avro schema used */
  def toAvroRDD(): (JavaRDD[Array[Byte]], String) = PythonTranslator.toPython(rdd)

  def layerMetadata: String = rdd.metadata.toJson.prettyPrint

  def reproject(
    crs: String, scheme: String, tile_size: Int, resampleMethod: String,
    resolutionThreshold: Double, extent: String, layout: String
  ): TiledRasterRDD[_]
}

class SpatialTiledRasterRDD(
  val zoomLevel: Option[Int],
  val rdd: RDD[(SpatialKey, MultibandTile)] with Metadata[TileLayerMetadata[SpatialKey]]
) extends TiledRasterRDD[SpatialKey] {

  def reproject(
    crs: String, scheme: String, tileSize: Int, resampleMethod: String,
    resolutionThreshold: Double, extent: String, layout: String
  ): TiledRasterRDD[SpatialKey] = {
    val _crs = Option(crs).flatMap(TileRDD.getCRS).get
    val _extent = Option(extent).flatMap(_.parseJson.convertTo[Option[Extent]])
    val _layout = Option(layout).flatMap(_.parseJson.convertTo[Option[TileLayout]])

    val schemeOrLayout: Either[LayoutScheme, LayoutDefinition] =
      (scheme, _layout, _extent) match {
        case ("float", Some(layout), Some(extent)) =>
          Right(LayoutDefinition(extent, layout))
        case ("float", _, _) =>
          Left(FloatingLayoutScheme(tileSize))
        case ("zoom", _, _) =>
          Left(ZoomedLayoutScheme(_crs, tileSize, resolutionThreshold))
        case _ =>
          throw new IllegalArgumentException(s"Unable to handle $scheme as layout scheme")
      }
    import Reproject.Options
    // TODO: return the zoom as well as RDD
    val (zoom, reprojected) = TileRDDReproject(rdd, _crs, schemeOrLayout, Options.DEFAULT)
    new SpatialTiledRasterRDD(Some(zoom), reprojected)
  }

}


class TemporalTiledRasterRDD(
  val zoomLevel: Option[Int],
  val rdd: RDD[(SpaceTimeKey, MultibandTile)] with Metadata[TileLayerMetadata[SpaceTimeKey]]
) extends TiledRasterRDD[SpaceTimeKey] {

  def reproject(
    crs: String, scheme: String, tileSize: Int, resampleMethod: String,
    resolutionThreshold: Double, extent: String, layout: String
  ): TiledRasterRDD[SpaceTimeKey] = ???
}
