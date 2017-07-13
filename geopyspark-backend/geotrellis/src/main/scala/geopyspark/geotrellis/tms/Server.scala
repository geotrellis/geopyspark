package geopyspark.geotrellis.tms

import akka.actor.ActorSystem
import akka.actor.Props
import akka.event.Logging
import akka.io.IO
import akka.http.scaladsl.Http
import akka.http.scaladsl.server.directives.DebuggingDirectives
import akka.stream.ActorMaterializer
import akka.http.scaladsl.Http.ServerBinding

import scala.concurrent._
import scala.concurrent.duration._
import java.net.{URI, URL, InetAddress}

import geotrellis.raster.render.ColorMap
import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.raster._
import org.apache.spark.rdd._

import scala.collection.immutable.HashMap
import scala.concurrent.ExecutionContext.Implicits.global
import scala.reflect._

object AkkaSystem {
  implicit val system = ActorSystem("geopyspark-tile-server")
  implicit val materializer = ActorMaterializer()

  trait LoggerExecutor {
    protected implicit val log = Logging(system, "tms")
  }
}

class TMSServer(router: TMSServerRoute) {
  import AkkaSystem._

  var _handshake = ""
  var binding: ServerBinding = null

  def localHost(): String = InetAddress.getLocalHost().getHostName()
  def host(): String = binding.localAddress.getHostName()
  def port(): Int = binding.localAddress.getPort()
  def unbind(): Unit = {
    Await.ready(binding.unbind, 10.seconds)
    binding = null
    router.shutdown
  }

  def bind(host: String): ServerBinding = {
    router.startup

    var futureBinding: scala.util.Try[Future[ServerBinding]] = null
    do {
      var portReq = scala.util.Random.nextInt(16383) + 49152
      futureBinding = scala.util.Try(Http()(system).bindAndHandle(router.route(this) , host, portReq))
    } while (futureBinding.isFailure)
    binding = Await.result(futureBinding.get, 10.seconds)
    binding
  }

  def bind(host: String, requestedPort: Int): ServerBinding = {
    router.startup

    val futureBinding = Http()(system).bindAndHandle(router.route(this) , host, requestedPort)
    binding = Await.result(futureBinding, 10.seconds)
    binding
  }

  def setHandshake(str: String) = { _handshake = str }
  def handshake(): String = _handshake
}

object TMSServer {
  def serveS3Catalog(bucket: String, root: String, catalog: String, cm: ColorMap): TMSServer = {
    import geotrellis.spark.io.s3._
    val reader = S3ValueReader(bucket, root)
    val route = new ValueReaderRoute(reader, catalog, new RenderFromCM(cm))
    new TMSServer(route)
  }

  def serveS3CatalogCustom(bucket: String, root: String, catalog: String, display: TileRender): TMSServer = {
    import geotrellis.spark.io.s3._
    val reader = S3ValueReader(bucket, root)
    val route = new ValueReaderRoute(reader, catalog, display)
    new TMSServer(route)
  }

  def serveRemoteTMSLayer(patternURL: String): TMSServer = {
    val route = new ExternalTMSServerRoute(patternURL)
    new TMSServer(route)
  }

  def serveSpatialRdd(levels: java.util.Map[Int, RDD[(SpatialKey, MultibandTile)]], cm: ColorMap, band: Int): TMSServer = {
    import scala.collection.JavaConverters._
    val level_map = levels.asScala.map { case (zoom, rdd) =>
      zoom -> rdd.map{ case (key, mbtile) => key -> mbtile.band(band) }
    }
    val route = new SpatialRddRoute(level_map, new RenderFromCM(cm), AkkaSystem.system)
    new TMSServer(route)
  }

  def serveSpatialRddCustom(levels: java.util.Map[Int, RDD[(SpatialKey, MultibandTile)]], display: TileRender, band: Int): TMSServer = {
    import scala.collection.JavaConverters._
    val level_map = levels.asScala.map { case (zoom, rdd) =>
      zoom -> rdd.map{ case (key, mbtile) => key -> mbtile.band(band) }
    }
    val route = new SpatialRddRoute(level_map, display, AkkaSystem.system)
    new TMSServer(route)
  }
}
