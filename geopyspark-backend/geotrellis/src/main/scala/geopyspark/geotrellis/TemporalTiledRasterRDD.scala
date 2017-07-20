package geopyspark.geotrellis

import geopyspark.geotrellis._
import geopyspark.geotrellis.GeoTrellisUtils._

import protos.tileMessages._
import protos.tupleMessages._

import geotrellis.proj4._
import geotrellis.raster._
import geotrellis.raster.distance._
import geotrellis.raster.histogram._
import geotrellis.raster.io.geotiff._
import geotrellis.raster.io.geotiff.compression._
import geotrellis.raster.rasterize._
import geotrellis.raster.render._
import geotrellis.raster.resample.ResampleMethod
import geotrellis.spark._
import geotrellis.spark.costdistance.IterativeCostDistance
import geotrellis.spark.io._
import geotrellis.spark.io.json._
import geotrellis.spark.mapalgebra.local._
import geotrellis.spark.mapalgebra.focal._
import geotrellis.spark.mask.Mask
import geotrellis.spark.pyramid._
import geotrellis.spark.reproject._
import geotrellis.spark.tiling._
import geotrellis.spark.util._
import geotrellis.util._
import geotrellis.vector._
import geotrellis.vector.io.wkb.WKB
import geotrellis.vector.triangulation._
import geotrellis.vector.voronoi._

import spray.json._
import spray.json.DefaultJsonProtocol._
import spire.syntax.cfor._

import com.vividsolutions.jts.geom.Coordinate
import org.apache.spark._
import org.apache.spark.api.java.JavaRDD
import org.apache.spark.rdd._
import org.apache.spark.SparkContext._

import java.util.ArrayList
import scala.reflect._
import scala.collection.JavaConverters._


class TemporalTiledRasterRDD(
  val zoomLevel: Option[Int],
  val rdd: RDD[(SpaceTimeKey, MultibandTile)] with Metadata[TileLayerMetadata[SpaceTimeKey]]
) extends TiledRasterRDD[SpaceTimeKey] {

  def resample_to_power_of_two(
    col_power: Int,
    row_power: Int,
    resampleMethod: ResampleMethod
  ): TiledRasterRDD[SpaceTimeKey] = {
    val cols = 1<<col_power
    val rows = 1<<row_power
    val rdd2 = rdd.mapValues({ tile => tile.resample(cols, rows, resampleMethod) })

    val metadata = rdd.metadata
    val layout = LayoutDefinition(
      metadata.extent,
      TileLayout(
        metadata.layout.tileLayout.layoutCols,
        metadata.layout.tileLayout.layoutRows,
        cols,
        rows
      )
    )
    val metadata2 = metadata.copy(layout = layout)

    TemporalTiledRasterRDD(None, ContextRDD(rdd2, metadata2))
  }

  def mask(geometries: Seq[MultiPolygon]): TiledRasterRDD[SpaceTimeKey] = {
    val options = Mask.Options.DEFAULT
    val singleBand = ContextRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )
    val result = Mask(singleBand, geometries, options)
    val multiBand = MultibandTileLayerRDD(
      result.mapValues({ v => MultibandTile(v) }),
      result.metadata
    )
    TemporalTiledRasterRDD(zoomLevel, multiBand)
  }

  def reproject(
    layout: LayoutDefinition,
    crs: CRS,
    options: Reproject.Options
  ): TiledRasterRDD[SpaceTimeKey] = {
    val (zoom, reprojected) = TileRDDReproject(rdd, crs, Right(layout), options)
    TemporalTiledRasterRDD(Some(zoom), reprojected)
  }

  def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: ResampleMethod
  ): TiledRasterRDD[SpaceTimeKey] = {
    val mapKeyTransform =
      MapKeyTransform(
        layoutDefinition.extent,
        layoutDefinition.layoutCols,
        layoutDefinition.layoutRows)

    val crs = rdd.metadata.crs

    val temporalRDD = rdd.map { x =>
      (TemporalProjectedExtent(mapKeyTransform(x._1), rdd.metadata.crs, x._1.instant), x._2)
    }

    val bounds = rdd.metadata.bounds.get
    val spatialBounds = KeyBounds(mapKeyTransform(rdd.metadata.extent))
    val retiledLayerMetadata = rdd.metadata.copy(
      layout = layoutDefinition,
      bounds = KeyBounds(
        minKey = bounds.minKey.setComponent[SpatialKey](spatialBounds.minKey),
        maxKey = bounds.maxKey.setComponent[SpatialKey](spatialBounds.maxKey)
      )
    )

    val tileLayer =
      MultibandTileLayerRDD(temporalRDD.tileToLayout(retiledLayerMetadata, resampleMethod), retiledLayerMetadata)

    TemporalTiledRasterRDD(None, tileLayer)
  }

  def pyramid(
    startZoom: Int,
    endZoom: Int,
    resampleMethod: ResampleMethod
  ): Array[TiledRasterRDD[SpaceTimeKey]] = {
    require(! rdd.metadata.bounds.isEmpty, "Can not pyramid an empty RDD")

    val scheme = ZoomedLayoutScheme(rdd.metadata.crs, rdd.metadata.tileRows)
    val part = rdd.partitioner.getOrElse(new HashPartitioner(rdd.partitions.length))

    val leveledList =
      Pyramid.levelStream(
        rdd,
        scheme,
        startZoom,
        endZoom,
        Pyramid.Options(resampleMethod=resampleMethod, partitioner=part)
      )

    leveledList.map{ x => TemporalTiledRasterRDD(Some(x._1), x._2) }.toArray
  }

  def focal(
    operation: String,
    neighborhood: String,
    param1: Double,
    param2: Double,
    param3: Double
  ): TiledRasterRDD[SpaceTimeKey] = {
    val singleTileLayerRDD: TileLayerRDD[SpaceTimeKey] = TileLayerRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    val _neighborhood = getNeighborhood(operation, neighborhood, param1, param2, param3)
    val cellSize = rdd.metadata.layout.cellSize
    val op: ((Tile, Option[GridBounds]) => Tile) = getOperation(operation, _neighborhood, cellSize, param1)

    val result: TileLayerRDD[SpaceTimeKey] = FocalOperation(singleTileLayerRDD, _neighborhood)(op)

    val multibandRDD: MultibandTileLayerRDD[SpaceTimeKey] =
      MultibandTileLayerRDD(result.mapValues{ x => MultibandTile(x) }, result.metadata)

    TemporalTiledRasterRDD(None, multibandRDD)
  }

  def costDistance(
    sc: SparkContext,
    geometries: Seq[Geometry],
    maxDistance: Double
  ): TiledRasterRDD[SpaceTimeKey] = {
    val singleTileLayer = TileLayerRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    implicit def convertion(k: SpaceTimeKey): SpatialKey =
      k.spatialKey

    implicit val _sc = sc

    val result: TileLayerRDD[SpaceTimeKey] =
      IterativeCostDistance(singleTileLayer, geometries, maxDistance)

    val multibandRDD: MultibandTileLayerRDD[SpaceTimeKey] =
      MultibandTileLayerRDD(result.mapValues{ x => MultibandTile(x) }, result.metadata)

    TemporalTiledRasterRDD(None, multibandRDD)
  }

  def hillshade(
    sc: SparkContext,
    azimuth: Double,
    altitude: Double,
    zFactor: Double,
    band: Int
  ): TiledRasterRDD[SpaceTimeKey] = {
    val tileLayer = TileLayerRDD(rdd.mapValues(_.band(band)), rdd.metadata)

    implicit val _sc = sc

    val result = tileLayer.hillshade(azimuth, altitude, zFactor)

    val multibandRDD: MultibandTileLayerRDD[SpaceTimeKey] =
      MultibandTileLayerRDD(result.mapValues(MultibandTile(_)), result.metadata)

    TemporalTiledRasterRDD(None, multibandRDD)
  }

  def reclassify(reclassifiedRDD: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def reclassifyDouble(reclassifiedRDD: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def withRDD(result: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(result, rdd.metadata))

  def toInt(converted: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toDouble(converted: RDD[(SpaceTimeKey, MultibandTile)]): TiledRasterRDD[SpaceTimeKey] =
    TemporalTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toProtoRDD(): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(SpaceTimeKey, MultibandTile), ProtoTuple](rdd)

  def toPngRDD(pngRDD: RDD[(SpaceTimeKey, Array[Byte])]): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(SpaceTimeKey, Array[Byte]), ProtoTuple](pngRDD)

  def toGeoTiffRDD(
    tags: Tags,
    geotiffOptions: GeoTiffOptions
  ): JavaRDD[Array[Byte]] = {
    val mapTransform = MapKeyTransform(
      rdd.metadata.layout.extent,
      rdd.metadata.layout.layoutCols,
      rdd.metadata.layout.layoutRows)

    val crs = rdd.metadata.crs

    val geotiffRDD = rdd.map { x =>
      val transKey = TemporalProjectedExtent(mapTransform(x._1), crs, x._1.instant)

      (x._1, MultibandGeoTiff(x._2, transKey.extent, transKey.crs, tags, geotiffOptions).toByteArray)
    }

    PythonTranslator.toPython[(SpaceTimeKey, Array[Byte]), ProtoTuple](geotiffRDD)
  }
}

object TemporalTiledRasterRDD {
  def fromProtoEncodedRDD(
    javaRDD: JavaRDD[Array[Byte]],
    metadata: String
  ): TemporalTiledRasterRDD = {
    val md = metadata.parseJson.convertTo[TileLayerMetadata[SpaceTimeKey]]
    val tileLayer = MultibandTileLayerRDD(
      PythonTranslator.fromPython[(SpaceTimeKey, MultibandTile), ProtoTuple](javaRDD, ProtoTuple.parseFrom), md)

    TemporalTiledRasterRDD(None, tileLayer)
  }

  def apply(
    zoomLevel: Option[Int],
    rdd: RDD[(SpaceTimeKey, MultibandTile)] with Metadata[TileLayerMetadata[SpaceTimeKey]]
  ): TemporalTiledRasterRDD =
    new TemporalTiledRasterRDD(zoomLevel, rdd)

  def rasterize(
    sc: SparkContext,
    geometryBytes: Array[Byte],
    extent: java.util.Map[String, Double],
    crs: String,
    instant: Int,
    cols: Int,
    rows: Int,
    fillValue: Int
  ): TiledRasterRDD[SpaceTimeKey] = {
    val rasterExtent = RasterExtent(extent.toExtent, cols, rows)
    val temporalExtent =
      TemporalProjectedExtent(rasterExtent.extent, TileRDD.getCRS(crs).get, instant.toInt)

    val tile = Rasterizer.rasterizeWithValue(WKB.read(geometryBytes), rasterExtent, fillValue)
    val rdd = sc.parallelize(Array((temporalExtent, MultibandTile(tile))))
    val tileLayout = TileLayout(1, 1, cols, rows)
    val layoutDefinition = LayoutDefinition(rasterExtent.extent, tileLayout)

    val metadata = rdd.collectMetadata[SpaceTimeKey](layoutDefinition)

    TemporalTiledRasterRDD(None, MultibandTileLayerRDD(rdd.tileToLayout(metadata), metadata))
  }

}
