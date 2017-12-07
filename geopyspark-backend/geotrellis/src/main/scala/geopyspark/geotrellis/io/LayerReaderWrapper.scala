package geopyspark.geotrellis.io

import geopyspark.geotrellis._

import geotrellis.vector._
import geotrellis.vector.io.wkt.WKT
import geotrellis.vector.io.wkb.WKB
import geotrellis.raster._
import geotrellis.proj4._
import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.spark.io.accumulo._
import geotrellis.spark.io.cassandra._
import geotrellis.spark.io.file._
import geotrellis.spark.io.hadoop._
import geotrellis.spark.io.hbase._
import geotrellis.spark.io.json._
import geotrellis.spark.io.s3._

import org.apache.spark._
import org.apache.spark.api.java.JavaRDD
import org.apache.spark.rdd.RDD

import spray.json._

import java.time.ZonedDateTime
import java.util.ArrayList
import scala.collection.JavaConverters._
import scala.collection.mutable


class LayerReaderWrapper(sc: SparkContext) {

  def query(
    attributeStore: AttributeStore,
    catalogUri: String,
    layerName: String,
    zoom: Int,
    queryGeometryBytes: Array[Byte],
    queryIntervalStrings: ArrayList[String],
    projQuery: String,
    numPartitions: Integer
  ): TiledRasterLayer[_] = {
    val id = LayerId(layerName, zoom)
    val spatialQuery: Option[Geometry] = Option(queryGeometryBytes).map(WKB.read)
    val queryCRS: Option[CRS] = TileLayer.getCRS(projQuery)
    val header = attributeStore.readHeader[LayerHeader](id)
    val layerReader: FilteringLayerReader[LayerId] = LayerReader(attributeStore, catalogUri)(sc)

    //val pyZoom: Option[Int] = ??? // is this top level zoom or zoom with None ?

    def getNumPartitions[K: SpatialComponent, M](
      layerQuery: LayerQuery[K, TileLayerMetadata[K]],
      layerMetadata: TileLayerMetadata[K]
    ): Int =
      Option(numPartitions).map(_.toInt).getOrElse {
        val tileBytes = (layerMetadata.cellType.bytes
          * layerMetadata.layout.tileLayout.tileCols
          * layerMetadata.layout.tileLayout.tileRows)
        // Aim for ~16MB per partition
        val tilesPerPartition = (1 << 24) / tileBytes
        // TODO: consider temporal dimension size as well
        val expectedTileCounts: Seq[Long] = layerQuery(layerMetadata).map(_.toGridBounds.sizeLong)
        try {
          math.max(1, (expectedTileCounts.reduce( _ + _) / tilesPerPartition).toInt)
        } catch {
          case e: java.lang.UnsupportedOperationException => 1
        }
      }

    header.keyClass match {
      case "geotrellis.spark.SpatialKey" =>
        val layerMetadata = attributeStore.readMetadata[TileLayerMetadata[SpatialKey]](id)
        var query = new LayerQuery[SpatialKey, TileLayerMetadata[SpatialKey]]

        for (geom <- spatialQuery) {
          query = applySpatialFilter(query, geom, layerMetadata.crs, queryCRS)
        }

        val numPartitions: Int = getNumPartitions(query, layerMetadata)

        val rdd =
          header.valueClass match {
            case "geotrellis.raster.Tile" =>
              layerReader.read[SpatialKey, Tile, TileLayerMetadata[SpatialKey]](id, query, numPartitions)
                .withContext(_.mapValues{ MultibandTile(_) })

            case "geotrellis.raster.MultibandTile" =>
              layerReader.read[SpatialKey, MultibandTile, TileLayerMetadata[SpatialKey]](id, query, numPartitions)
          }

        new SpatialTiledRasterLayer(Some(zoom), rdd)

      case "geotrellis.spark.SpaceTimeKey" =>
        val layerMetadata = attributeStore.readMetadata[TileLayerMetadata[SpaceTimeKey]](id)
        var query = new LayerQuery[SpaceTimeKey, TileLayerMetadata[SpaceTimeKey]]

        for (geom <- spatialQuery) {
          query = applySpatialFilter(query, geom, layerMetadata.crs, queryCRS)
        }

        for (intervals <- getTemporalQuery(queryIntervalStrings)) {
          query = query.where(intervals)
        }

        val numPartitions: Int = getNumPartitions(query, layerMetadata)

        val rdd =
          header.valueClass match {
            case "geotrellis.raster.Tile" =>
              layerReader.read[SpaceTimeKey, Tile, TileLayerMetadata[SpaceTimeKey]](id, query, numPartitions)
                .withContext(_.mapValues{ MultibandTile(_) })

            case "geotrellis.raster.MultibandTile" =>
              layerReader.read[SpaceTimeKey, MultibandTile, TileLayerMetadata[SpaceTimeKey]](id, query, numPartitions)
          }

        new TemporalTiledRasterLayer(Some(zoom), rdd)
    }
  }

  private def applySpatialFilter[K: SpatialComponent: Boundable, M](
    layerQuery: LayerQuery[K, M],
    queryGeom: Geometry,
    layerCRS: CRS,
    queryCRS: Option[CRS]
  )(implicit
    ev0: LayerFilter[K, Contains.type, Point, M],
    ev1: LayerFilter[K, Intersects.type, Polygon, M],
    ev2: LayerFilter[K, Intersects.type, MultiPolygon, M]
  ): LayerQuery[K, M] = {
    val projectedGeom =
      queryCRS match {
        case Some(crs) =>
          queryGeom.reproject(crs, layerCRS)
        case None =>
          queryGeom
      }

    projectedGeom match {
      case point: Point =>
        layerQuery.where(Contains(point) or Contains(point))
      case polygon: Polygon =>
        layerQuery.where(Intersects(polygon))
      case multi: MultiPolygon =>
        layerQuery.where(Intersects(multi))
      case _ => layerQuery
    }
  }

  private def getTemporalQuery(queryIntervalStrings: ArrayList[String]): Option[LayerFilter.Or[Between.type,(ZonedDateTime, ZonedDateTime)]] = {
    val temporalRanges = queryIntervalStrings
      .asScala
      .grouped(2)
      .map({ list =>
        list match {
          case mutable.Buffer(a, b) =>
            Between(ZonedDateTime.parse(a), ZonedDateTime.parse(b))
          case mutable.Buffer(a) => {
            val zdt = ZonedDateTime.parse(a)
            val zdt1 = zdt.minusNanos(16)
            val zdt2 = zdt.plusNanos(17)
            Between(zdt1, zdt2)
          }
        }})
      .toList

    if (temporalRanges.length >= 2) {
      val h1 = temporalRanges.head
      val h2 = temporalRanges.tail.head
      Some(temporalRanges.drop(2).foldLeft(h1 or h2)({ (cs, c) => cs or c }))
    }
    else if (temporalRanges.length == 1) {
      val h1 = temporalRanges.head
      Some(h1 or h1)
    }
    else None
  }
}
