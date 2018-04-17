package geopyspark.geotools.kryo

import com.esotericsoftware.kryo.Kryo
import de.javakaffee.kryoserializers._
import geotrellis.spark.io.kryo._
import org.locationtech.geomesa.spark.GeoMesaSparkKryoRegistrator

class ExpandedKryoRegistrator extends KryoRegistrator {
  override def registerClasses(kryo: Kryo) = {
    UnmodifiableCollectionsSerializer.registerSerializers(kryo)
    (new GeoMesaSparkKryoRegistrator).registerClasses(kryo)
////    kryo.register(classOf[SimpleFeature])
////    kryo.register(classOf[SimpleFeatureImpl])
////    kryo.register(classOf[SimpleFeatureType])
//    super.registerClasses(kryo)
  }
//  override def registerClasses(kryo: Kryo): Unit = {
//    System.out.println("kryo")
////    super.registerClasses(kryo)
//  }
}
