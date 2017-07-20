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

class SpatialTiledRasterRDD(
  val zoomLevel: Option[Int],
  val rdd: RDD[(SpatialKey, MultibandTile)] with Metadata[TileLayerMetadata[SpatialKey]]
) extends TiledRasterRDD[SpatialKey] {

  def resample_to_power_of_two(
    col_power: Int,
    row_power: Int,
    resampleMethod: ResampleMethod
  ): TiledRasterRDD[SpatialKey] = {
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

    SpatialTiledRasterRDD(None, ContextRDD(rdd2, metadata2))
  }

  def lookup(
    col: Int,
    row: Int
  ): java.util.ArrayList[Array[Byte]] = {
    val tiles = rdd.lookup(SpatialKey(col, row))
    PythonTranslator.toPython[MultibandTile, ProtoMultibandTile](tiles)
  }

  def reproject(
    layout: LayoutDefinition,
    crs: CRS,
    options: Reproject.Options
  ): TiledRasterRDD[SpatialKey] = {
    val (zoom, reprojected) = TileRDDReproject(rdd, crs, Right(layout), options)
    SpatialTiledRasterRDD(Some(zoom), reprojected)
  }

  def tileToLayout(
    layoutDefinition: LayoutDefinition,
    resampleMethod: ResampleMethod
  ): TiledRasterRDD[SpatialKey] = {
    val mapKeyTransform =
      MapKeyTransform(
        layoutDefinition.extent,
        layoutDefinition.layoutCols,
        layoutDefinition.layoutRows)

    val crs = rdd.metadata.crs
    val projectedRDD = rdd.map{ x => (ProjectedExtent(mapKeyTransform(x._1), crs), x._2) }
    val retiledLayerMetadata = rdd.metadata.copy(
      layout = layoutDefinition,
      bounds = KeyBounds(mapKeyTransform(rdd.metadata.extent))
    )

    val tileLayer =
      MultibandTileLayerRDD(projectedRDD.tileToLayout(retiledLayerMetadata, resampleMethod), retiledLayerMetadata)

    SpatialTiledRasterRDD(None, tileLayer)
  }

  def pyramid(
    startZoom: Int,
    endZoom: Int,
    resampleMethod: ResampleMethod
  ): Array[TiledRasterRDD[SpatialKey]] = {
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

    leveledList.map{ x => SpatialTiledRasterRDD(Some(x._1), x._2) }.toArray
  }

  def focal(
    operation: String,
    neighborhood: String,
    param1: Double,
    param2: Double,
    param3: Double
  ): TiledRasterRDD[SpatialKey] = {
    val singleTileLayerRDD: TileLayerRDD[SpatialKey] = TileLayerRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    val _neighborhood = getNeighborhood(operation, neighborhood, param1, param2, param3)
    val cellSize = rdd.metadata.layout.cellSize
    val op: ((Tile, Option[GridBounds]) => Tile) = getOperation(operation, _neighborhood, cellSize, param1)

    val result: TileLayerRDD[SpatialKey] = FocalOperation(singleTileLayerRDD, _neighborhood)(op)

    val multibandRDD: MultibandTileLayerRDD[SpatialKey] =
      MultibandTileLayerRDD(result.mapValues{ x => MultibandTile(x) }, result.metadata)

    SpatialTiledRasterRDD(None, multibandRDD)
  }

  def mask(geometries: Seq[MultiPolygon]): TiledRasterRDD[SpatialKey] = {
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
    SpatialTiledRasterRDD(zoomLevel, multiBand)
  }

  def stitch: Array[Byte] = {
    val contextRDD = ContextRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    PythonTranslator.toPython[Tile, ProtoTile](contextRDD.stitch.tile)
  }

  def save_stitched(path: String): Unit =
    _save_stitched(path, None, None)

  def save_stitched(path: String, cropBounds: ArrayList[Double]): Unit =
    _save_stitched(path, Some(cropBounds), None)

  def save_stitched(path: String, cropBounds: ArrayList[Double], cropDimensions: ArrayList[Int]): Unit =
    _save_stitched(path, Some(cropBounds), Some(cropDimensions))

  private def _save_stitched(path: String, cropBounds: Option[ArrayList[Double]], cropDimensions: Option[ArrayList[Int]]): Unit = {

    val contextRDD = ContextRDD(
      rdd.map({ case (k, v) => (k, v.band(0)) }),
      rdd.metadata
    )
    val stitched: Raster[Tile] = contextRDD.stitch()

    val adjusted = {
      val cropExtent =
        cropBounds.map { b =>
          val bounds = b.asScala.toArray
          Extent(bounds(0), bounds(1), bounds(2), bounds(3))
        }

      val cropped =
        cropExtent match {
          case Some(extent) =>
            stitched.crop(extent)
          case None =>
            stitched
        }

      val resampled =
        cropDimensions.map(_.asScala.toArray) match {
          case Some(dimensions) =>
            cropped.resample(dimensions(0), dimensions(1))
          case None =>
            cropped
        }

      resampled
    }

    GeoTiff(adjusted, contextRDD.metadata.crs).write(path)
  }

  def costDistance(
    sc: SparkContext,
    geometries: Seq[Geometry],
    maxDistance: Double
  ): TiledRasterRDD[SpatialKey] = {
    val singleTileLayer = TileLayerRDD(
      rdd.mapValues({ v => v.band(0) }),
      rdd.metadata
    )

    implicit def conversion(k: SpaceTimeKey): SpatialKey =
      k.spatialKey

    implicit val _sc = sc

    val result: TileLayerRDD[SpatialKey] =
      IterativeCostDistance(singleTileLayer, geometries, maxDistance)

    val multibandRDD: MultibandTileLayerRDD[SpatialKey] =
      MultibandTileLayerRDD(result.mapValues{ x => MultibandTile(x) }, result.metadata)

    SpatialTiledRasterRDD(None, multibandRDD)
  }

  def hillshade(
    sc: SparkContext,
    azimuth: Double,
    altitude: Double,
    zFactor: Double,
    band: Int
  ): TiledRasterRDD[SpatialKey] = {
    val tileLayer = TileLayerRDD(rdd.mapValues(_.band(band)), rdd.metadata)

    implicit val _sc = sc

    val result = tileLayer.hillshade(azimuth, altitude, zFactor)

    val multibandRDD: MultibandTileLayerRDD[SpatialKey] =
      MultibandTileLayerRDD(result.mapValues{ tile => MultibandTile(tile) }, result.metadata)

    SpatialTiledRasterRDD(None, multibandRDD)
  }

  def reclassify(reclassifiedRDD: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def reclassifyDouble(reclassifiedRDD: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(reclassifiedRDD, rdd.metadata))

  def withRDD(result: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(result, rdd.metadata))

  def toInt(converted: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toDouble(converted: RDD[(SpatialKey, MultibandTile)]): TiledRasterRDD[SpatialKey] =
    SpatialTiledRasterRDD(zoomLevel, MultibandTileLayerRDD(converted, rdd.metadata))

  def toProtoRDD(): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(SpatialKey, MultibandTile), ProtoTuple](rdd)

  def toPngRDD(pngRDD: RDD[(SpatialKey, Array[Byte])]): JavaRDD[Array[Byte]] =
    PythonTranslator.toPython[(SpatialKey, Array[Byte]), ProtoTuple](pngRDD)

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
      val transKey = ProjectedExtent(mapTransform(x._1), crs)

      (x._1, MultibandGeoTiff(x._2, transKey.extent, transKey.crs, tags, geotiffOptions).toByteArray)
    }

    PythonTranslator.toPython[(SpatialKey, Array[Byte]), ProtoTuple](geotiffRDD)
  }
}


object SpatialTiledRasterRDD {
  def fromProtoEncodedRDD(
    javaRDD: JavaRDD[Array[Byte]],
    metadata: String
  ): SpatialTiledRasterRDD = {
    val md = metadata.parseJson.convertTo[TileLayerMetadata[SpatialKey]]
    val tileLayer = MultibandTileLayerRDD(
      PythonTranslator.fromPython[(SpatialKey, MultibandTile), ProtoTuple](javaRDD, ProtoTuple.parseFrom), md)

    SpatialTiledRasterRDD(None, tileLayer)
  }

  def apply(
    zoomLevel: Option[Int],
    rdd: RDD[(SpatialKey, MultibandTile)] with Metadata[TileLayerMetadata[SpatialKey]]
  ): SpatialTiledRasterRDD =
    new SpatialTiledRasterRDD(zoomLevel, rdd)

  def rasterizeGeometry(sc: SparkContext, geomWKB: ArrayList[Array[Byte]], geomCRSStr: String,
    requestedZoom: Int, fillValue: Double, cellTypeString: String, options: Rasterizer.Options,
    numPartitions: Integer
  ): TiledRasterRDD[SpatialKey]= {
    val cellType = CellType.fromName(cellTypeString)
    val geoms = geomWKB.asScala.map(WKB.read)
    val srcCRS = TileRDD.getCRS(geomCRSStr).get
    val LayoutLevel(z, ld) = ZoomedLayoutScheme(srcCRS).levelForZoom(requestedZoom)
    val maptrans = ld.mapTransform
    val fullEnvelope = geoms.map(_.envelope).reduce(_ combine _)
    val gb @ GridBounds(cmin, rmin, cmax, rmax) = maptrans(fullEnvelope)

    val geomsRdd = sc.parallelize(geoms)
    import geotrellis.raster.rasterize.Rasterizer.Options
    val tiles = RasterizeRDD.fromGeometry(
      geoms = geomsRdd,
      layout = ld,
      ct = cellType,
      value = fillValue,
      options = Option(options).getOrElse(Options.DEFAULT),
      numPartitions = Option(numPartitions).map(_.toInt).getOrElse(math.max(gb.size / 512, 1)))
    val metadata = TileLayerMetadata(cellType, ld, maptrans(gb), srcCRS, KeyBounds(gb))
    SpatialTiledRasterRDD(Some(requestedZoom),
      MultibandTileLayerRDD(tiles.mapValues(MultibandTile(_)), metadata))
  }

  def euclideanDistance(sc: SparkContext, geomWKB: Array[Byte], geomCRSStr: String, cellTypeString: String, requestedZoom: Int): TiledRasterRDD[SpatialKey]= {
    val cellType = CellType.fromName(cellTypeString)
    val geom = WKB.read(geomWKB)
    val srcCRS = TileRDD.getCRS(geomCRSStr).get
    val LayoutLevel(z, ld) = ZoomedLayoutScheme(srcCRS).levelForZoom(requestedZoom)
    val maptrans = ld.mapTransform
    val gb @ GridBounds(cmin, rmin, cmax, rmax) = maptrans(geom.envelope)

    val keys = for (r <- rmin to rmax; c <- cmin to cmax) yield SpatialKey(c, r)

    val pts =
      if (geom.isInstanceOf[MultiPoint]) {
        geom.asInstanceOf[MultiPoint].points.map(_.jtsGeom.getCoordinate)
      } else {
        val coords = collection.mutable.ListBuffer.empty[Coordinate]

        def createPoints(sk: SpatialKey) = {
          val ex = maptrans(sk)
          val re = RasterExtent(ex, ld.tileCols, ld.tileRows)

          def rasterizeToPoints(px: Int, py: Int): Unit = {
            val (x, y) = re.gridToMap(px, py)
            val coord = new Coordinate(x, y)
            coords += coord
          }

          Rasterizer.foreachCellByGeometry(geom, re)(rasterizeToPoints)
        }

        keys.foreach(createPoints)
        coords.toArray
      }

    val dt = KryoWrapper(DelaunayTriangulation(pts))
    val skRDD = sc.parallelize(keys)
    val mbtileRDD: RDD[(SpatialKey, MultibandTile)] = skRDD.mapPartitions({ skiter => skiter.map { sk =>
      val ex = maptrans(sk)
      val re = RasterExtent(ex, ld.tileCols, ld.tileRows)
      val tile = ArrayTile.empty(cellType, re.cols, re.rows)
      val vd = new VoronoiDiagram(dt.value, ex)
      vd.voronoiCellsWithPoints.foreach(EuclideanDistanceTile.rasterizeDistanceCell(re, tile)(_))
      (sk, MultibandTile(tile))
    } }, preservesPartitioning=true)

    val metadata = TileLayerMetadata(cellType, ld, maptrans(gb), srcCRS, KeyBounds(gb))

    SpatialTiledRasterRDD(Some(z), MultibandTileLayerRDD(mbtileRDD, metadata))
  }
}
