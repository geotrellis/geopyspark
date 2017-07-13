package geopyspark.geotrellis.tms

import geotrellis.raster._
import geotrellis.raster.render._
import geotrellis.spark._
import geotrellis.spark.io._
import geotrellis.vector._

import akka.actor.{Actor, ActorRef, ActorSystem, Props}
import akka.http.scaladsl.marshallers.sprayjson.SprayJsonSupport._
import akka.http.scaladsl.marshallers.sprayjson.SprayJsonSupport
import akka.http.scaladsl.marshalling.{ToResponseMarshaller, ToResponseMarshallable}
import akka.http.scaladsl.model.{ContentType, HttpEntity, HttpResponse, MediaTypes, StatusCodes}
import akka.http.scaladsl.model.MediaTypes.{`image/png`, `text/plain`}
import akka.http.scaladsl.server.{Route, Directives}
import akka.http.scaladsl.unmarshalling.Unmarshaller._
import akka.pattern.{ask, pipe}
import akka.util.Timeout
import org.apache.spark.rdd._
import org.apache.spark.{SparkConf, SparkContext}
import spray.json._
import spray.json.DefaultJsonProtocol

import scala.collection.JavaConversions._
import scala.concurrent.{Await, ExecutionContext, Future, Promise}
import scala.concurrent.duration._
import scala.concurrent.ExecutionContext.Implicits.global
import scala.collection.immutable.HashMap
import scala.collection.concurrent._
import scala.util.Try

trait TMSServerRoute extends Directives with AkkaSystem.LoggerExecutor {
  def startup(): Unit = {}
  def shutdown(): Unit = {}

  def root: Route
  def route(server: TMSServer): Route = {
    get { root ~ path("handshake") { complete { server.handshake } } }
  }

  def time[T](msg: String)(f: => T) = {
    val start = System.currentTimeMillis
    val v = f
    val end = System.currentTimeMillis
    println(s"[TIMING] $msg: ${java.text.NumberFormat.getIntegerInstance.format(end - start)} ms")
    v
  }
}

class ValueReaderRoute(
  valueReader: ValueReader[LayerId],
  catalog: String,
  rf: TileRender
) extends TMSServerRoute {

  val reader = valueReader
  val layers = TrieMap.empty[Int, Reader[SpatialKey, Tile]]
  def root: Route =
    pathPrefix("tile" / IntNumber / IntNumber / IntNumber) { (zoom, x, y) =>
      val key = SpatialKey(x, y)
      complete {
        Future {
          val reader = layers.getOrElseUpdate(zoom, valueReader.reader[SpatialKey, Tile](LayerId(catalog, zoom)))
          val tile: Tile = reader(key)
          val bytes: Array[Byte] = time(s"Rendering tile @ $key (zoom=$zoom)"){
            if (rf.requiresEncoding()) {
              // println("Encoding version")
              rf.renderEncoded(geopyspark.geotrellis.PythonTranslator.toPython(MultibandTile(tile)))
            } else {
              // println("Non-encoding version")
              rf.render(MultibandTile(tile)) 
            }
          }
          // println(s"Got back $bytes from renderer")
          HttpEntity(`image/png`, bytes)
        }
      }
    }
}

class ExternalTMSServerRoute(patternURL: String) extends TMSServerRoute {
  def root: Route =
    pathPrefix("tile" / IntNumber / IntNumber / IntNumber) { (zoom, x, y) =>
      val newUrl = patternURL.replace("{z}", zoom.toString)
                             .replace("{x}", x.toString)
                             .replace("{y}", y.toString)
      redirect(newUrl, StatusCodes.SeeOther)
    }
}


sealed trait AggregatorCommand
case class QueueRequest(zoom: Int, x: Int, y: Int, pr: Promise[Option[HttpResponse]]) extends AggregatorCommand
case object DumpRequests extends AggregatorCommand

object RequestAggregator {
  def props = Props(new RequestAggregator)
}

class RequestAggregator extends Actor {
  val requests = scala.collection.mutable.ListBuffer.empty[QueueRequest]

  def receive = {
    case qr @ QueueRequest(zoom, x, y, pr) => 
      requests += qr
    case DumpRequests => 
      sender ! FulfillRequests(requests.toSeq)
      requests.clear
    case _ => println("Unexpected message!")
  }

  def queueRequest(qr: QueueRequest): Unit = {
    val QueueRequest(zoom, x, y, pr) = qr
  }
}

sealed trait FulfillerCommand
case object Initialize extends FulfillerCommand
case class FulfillRequests(reqs: Seq[QueueRequest]) extends AggregatorCommand

object RDDLookup {
  val interval = 150 milliseconds
  def props(levels: scala.collection.mutable.Map[Int, RDD[(SpatialKey, Tile)]], rf: TileRender, aggregator: ActorRef) = Props(new RDDLookup(levels, rf, aggregator))
}

class RDDLookup(
  levels: scala.collection.mutable.Map[Int, RDD[(SpatialKey, Tile)]], 
  rf: TileRender,
  aggregator: ActorRef
)(implicit ec: ExecutionContext) extends Actor {
  def receive = {
    case Initialize =>
      context.system.scheduler.scheduleOnce(RDDLookup.interval, aggregator, DumpRequests)
    case FulfillRequests(requests) => 
      fulfillRequests(requests)
      context.system.scheduler.scheduleOnce(RDDLookup.interval, aggregator, DumpRequests)
  }

  def fulfillRequests(requests: Seq[QueueRequest]) = {
    if (requests nonEmpty) {
      requests
        .groupBy{ case QueueRequest(zoom, _, _, _) => zoom }
        .foreach{ case (zoom, reqs) => {
          levels.get(zoom) match {
            case Some(rdd) =>
              val kps = reqs.map{ case QueueRequest(_, x, y, promise) => (SpatialKey(x, y), promise) }
              val keys = reqs.map{ case QueueRequest(_, x, y, _) => SpatialKey(x, y) }.toSet
              val results = rdd.filter{ elem => keys.contains(elem._1) }.collect()
              kps.foreach{ case (key, promise) => {
                promise success (results
                  .find{ case (rddKey, _) => rddKey == key } 
                  .map{ case (_, tile) => 
                        val bytes: Array[Byte] =
                          if (rf.requiresEncoding()) {
                            rf.renderEncoded(geopyspark.geotrellis.PythonTranslator.toPython(MultibandTile(tile)))
                          } else {
                            rf.render(MultibandTile(tile)) 
                          }
                        HttpResponse(entity = HttpEntity(ContentType(MediaTypes.`image/png`), bytes)) 
                      }
                )
              }}
            case None =>
              reqs.foreach{ case QueueRequest(_, _, _, promise) => promise success None }
          }
        }}
    }
  }
}

class SpatialRddRoute(
  levels: scala.collection.mutable.Map[Int, RDD[(SpatialKey, Tile)]],
  rf: TileRender,
  system: ActorSystem
) extends TMSServerRoute {
  import java.util.UUID

  implicit val executionContext: ExecutionContext = system.dispatchers.lookup("custom-blocking-dispatcher")  

  private var _aggregator: ActorRef = null
  private var _fulfiller: ActorRef = null

  override def startup() = {
    if (_aggregator != null) 
      throw new IllegalStateException("Cannot start: TMS server already running")

    _aggregator = system.actorOf(RequestAggregator.props, UUID.randomUUID.toString)
    _fulfiller = system.actorOf(RDDLookup.props(levels, rf, aggregator), UUID.randomUUID.toString)
    _fulfiller ! Initialize
  }

  override def shutdown() = {
    if (_aggregator == null)
      throw new IllegalStateException("Cannot stop: TMS server not running")

    system.stop(_aggregator)
    system.stop(_fulfiller)
    _aggregator = null
    _fulfiller = null
  }

  def aggregator = _aggregator
  def fulfiller = _fulfiller

  def root: Route =
    pathPrefix("tile" / IntNumber / IntNumber / IntNumber) { (zoom, x, y) =>
      val callback = Promise[Option[HttpResponse]]()
      aggregator ! QueueRequest(zoom, x, y, callback) 
      complete { 
        callback.future
      }
    }

}

