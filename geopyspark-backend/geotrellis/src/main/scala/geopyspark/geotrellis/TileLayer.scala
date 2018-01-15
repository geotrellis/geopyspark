package geopyspark.geotrellis

import Constants._
import geopyspark.geotrellis.GeoTrellisUtils._
import geotrellis.proj4._
import geotrellis.raster._
import geotrellis.raster.mapalgebra.focal._
import geotrellis.raster.render._
import geotrellis.raster.histogram._
import geotrellis.raster.io.geotiff._
import geotrellis.raster.io.geotiff.compression._
import geotrellis.raster.resample.ResampleMethod
import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.spark.tiling._
import geotrellis.vector._
import org.apache.spark._
import org.apache.spark.api.java.JavaRDD
import org.apache.spark.rdd._
import org.apache.spark.storage.StorageLevel
import protos.tupleMessages.ProtoTuple

import scala.util.{Either, Left, Right}
import spray.json._
import spire.syntax.order._
import spire.std.any._

import scala.reflect.{ClassTag, classTag}
import scala.collection.JavaConverters._
import scala.util.Try

import java.util.ArrayList

abstract class TileLayer[K: ClassTag] {
  def rdd: RDD[(K, MultibandTile)]
  def keyClass: Class[_] = classTag[K].runtimeClass
  def keyClassName: String = keyClass.getName

  def partitioner: String =
    rdd.partitioner match {
      case Some(p) => TileLayer.toPythonPartitioner(p)
      case None => null
    }

  def toPngRDD(cm: ColorMap): JavaRDD[Array[Byte]] =
    toPngRDD(rdd.mapValues { v => v.bands(0).renderPng(cm).bytes })

  def toPngRDD(pngRDD: RDD[(K, Array[Byte])]): JavaRDD[Array[Byte]]

  def toGeoTiffRDD(
    storageMethod: StorageMethod,
    compression: String,
    colorSpace: Int,
    headTags: java.util.Map[String, String],
    bandTags: java.util.ArrayList[java.util.Map[String, String]]
  ): JavaRDD[Array[Byte]] = {
    val tags =
      if (headTags.isEmpty || bandTags.isEmpty)
        Tags.empty
      else
        Tags(headTags.asScala.toMap,
          bandTags.toArray.map(_.asInstanceOf[scala.collection.immutable.Map[String, String]]).toList)

    val options = GeoTiffOptions(
      storageMethod,
      TileLayer.getCompression(compression),
      colorSpace,
      None)

    toGeoTiffRDD(tags, options)
  }

  def toGeoTiffRDD(
    storageMethod: StorageMethod,
    compression: String,
    colorSpace: Int,
    colorMap: ColorMap,
    headTags: java.util.Map[String, String],
    bandTags: java.util.ArrayList[java.util.Map[String, String]]
  ): JavaRDD[Array[Byte]] = {
    val tags =
      if (headTags.isEmpty || bandTags.isEmpty)
        Tags.empty
      else
        Tags(headTags.asScala.toMap,
          bandTags.toArray.map(_.asInstanceOf[scala.collection.immutable.Map[String, String]]).toList)

    val options = GeoTiffOptions(
      storageMethod,
      TileLayer.getCompression(compression),
      colorSpace,
      Some(IndexedColorMap.fromColorMap(colorMap)))

    toGeoTiffRDD(tags, options)
  }

  def toGeoTiffRDD(tags: Tags, geotiffOptions: GeoTiffOptions): JavaRDD[Array[Byte]]

  def reclassify(
    intMap: java.util.Map[Int, Int],
    boundaryType: String,
    replaceNoDataWith: Int
  ): TileLayer[_] = {
    val scalaMap = intMap.asScala.toMap

    val boundary = getBoundary(boundaryType)
    val mapStrategy = new MapStrategy(boundary, replaceNoDataWith, NODATA, false)
    val breakMap = new BreakMap(scalaMap, mapStrategy, { i: Int => isNoData(i) })

    val reclassifiedRDD =
      rdd.mapValues { x =>
        val count = x.bandCount
        val tiles = Array.ofDim[Tile](count)

        for (y <- 0 until count) {
          val band = x.band(y)
          tiles(y) = band.map(i => breakMap.apply(i))
        }

        MultibandTile(tiles)
      }
    reclassify(reclassifiedRDD)
  }

  def persist(newLevel: StorageLevel): Unit = {
    // persist call changes the state of the SparkContext rather than RDD object
    rdd.persist(newLevel)
  }

  def unpersist(): Unit = {
    rdd.unpersist()
  }

  def reclassifyDouble(
    doubleMap: java.util.Map[Double, Double],
    boundaryType: String,
    replaceNoDataWith: Double
  ): TileLayer[_] = {
    val scalaMap = doubleMap.asScala.toMap

    val boundary = getBoundary(boundaryType)
    val mapStrategy = new MapStrategy(boundary, replaceNoDataWith, doubleNODATA, false)
    val breakMap = new BreakMap(scalaMap, mapStrategy, { d: Double => isNoData(d) })

    val reclassifiedRDD =
      rdd.mapValues { x =>
        val count = x.bandCount
        val tiles = Array.ofDim[Tile](count)

        for (y <- 0 until count) {
          val band = x.band(y)
          tiles(y) = band.mapDouble(i => breakMap.apply(i))
        }

        MultibandTile(tiles)
      }
    reclassifyDouble(reclassifiedRDD)
  }

  def getMinMax: (Double, Double) = {
    val minMaxs: Array[(Double, Double)] =
      rdd.histogram.map { x =>
        x.minMaxValues match {
          case None => (Double.NaN, Double.NaN)
          case Some(minMaxs) => minMaxs
        }
      }

    minMaxs.foldLeft(minMaxs(0)) { (acc, elem) =>
      if (isData(elem._1)) {
        (math.min(acc._1, elem._1), math.max(acc._2, elem._2))
      } else {
        acc
      }
    }
  }

  /** Compute the quantile breaks per band.
   * TODO: This just works for single bands right now.
   *       make it work with multiband.
   */
  def quantileBreaks(n: Int): Array[Double] =
    rdd
      .histogram
      .head
      .quantileBreaks(n)

  /** Compute the quantile breaks per band.
   * TODO: This just works for single bands right now.
   *       make it work with multiband.
   */
  def quantileBreaksExactInt(n: Int): Array[Int] =
    rdd
      .mapValues(_.band(0))
      .histogramExactInt
      .quantileBreaks(n)


  def getIntHistograms(): Array[Histogram[Int]] = rdd.histogramExactInt

  def getDoubleHistograms(): Array[Histogram[Double]] = rdd.histogram

  protected def reclassify(reclassifiedRDD: RDD[(K, MultibandTile)]): TileLayer[_]
  protected def reclassifyDouble(reclassifiedRDD: RDD[(K, MultibandTile)]): TileLayer[_]
}

object TileLayer {
  import Constants._

  def getResampleMethod(resampleMethod: String): ResampleMethod = {
    import geotrellis.raster.resample._

    resampleMethod match {
      case NEARESTNEIGHBOR => NearestNeighbor
      case BILINEAR => Bilinear
      case CUBICCONVOLUTION => CubicConvolution
      case CUBICSPLINE => CubicSpline
      case LANCZOS => Lanczos
      case AVERAGE => Average
      case MODE => Mode
      case MEDIAN => Median
      case MAX => Max
      case MIN => Min
    }
  }

  def getCRS(crs: String): Option[CRS] = {
    Option(crs).flatMap { crs =>
      Try(CRS.fromName(crs))
        .recover({ case e => CRS.fromString(crs) })
        .recover({ case e => CRS.fromEpsgCode(crs.toInt) })
        .toOption
    }
  }

  def getStorageMethod(
    storageMethod: String,
    rowsPerStrip: Int,
    tileDimensions: java.util.ArrayList[Int]
  ): StorageMethod =
    (storageMethod, rowsPerStrip) match {
      case (STRIPED, 0) => Striped()
      case (STRIPED, x) => Striped(x)
      case (TILED, _) => Tiled(tileDimensions.get(0), tileDimensions.get(1))
    }

  def getCompression(compressionType: String): Compression =
    compressionType match {
      case NOCOMPRESSION => NoCompression
      case DEFLATECOMPRESSION => DeflateCompression
    }

  def getTarget(target: String): TargetCell =
    target match {
      case ALLCELLS => TargetCell.All
      case DATACELLS => TargetCell.Data
      case NODATACELLS => TargetCell.NoData
    }

  def getPartitioner(partitions: Int, partitioner: String): Partitioner =
    partitioner match {
      case HASH => new HashPartitioner(partitions)
      case SPATIAL => SpatialPartitioner(partitions)
    }

  def toPythonPartitioner(partitioner: Partitioner): String =
    partitioner match {
      case hp: HashPartitioner => HASH
      case sp: SpatialPartitioner[_] => SPATIAL
    }

  def combineBands[K: ClassTag, L <: TileLayer[K]: ClassTag](
    sc: SparkContext,
    layers: ArrayList[L]
  ): RDD[(K, MultibandTile)] = {
    val scalaLayers = layers.asScala.toArray

    val rdds: Array[RDD[(K, MultibandTile)]] =
      scalaLayers.map { case (v: L) => v.rdd }

    val arr = Array.ofDim[RDD[(K, (Int, MultibandTile))]](rdds.size)

    for ((layer, index) <- rdds.zipWithIndex) {
      arr(index) = layer.mapValues { (index, _) }
    }

    val unioned = sc.union(arr.toSeq)

    val bands: RDD[(K, Map[Int, Vector[Tile]])] =
      unioned.combineByKey(
        (value: (Int, MultibandTile)) =>
          Map(value._1 -> value._2.bands),
        (bandMap: Map[Int, Vector[Tile]], value: (Int, MultibandTile)) =>
          bandMap + (value._1 -> value._2.bands),
        (m1: Map[Int, Vector[Tile]], m2: Map[Int, Vector[Tile]]) =>
          m1 ++ m2
      )

    bands.mapValues { case (v: Map[Int, Vector[Tile]]) =>
      MultibandTile(
        v.toSeq
          .sortWith(_._1 < _._1)
          .map { case (_, values) => values }
          .flatten
        )
    }
  }
}
