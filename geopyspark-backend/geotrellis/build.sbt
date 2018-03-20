name := "geotrellis-backend"

libraryDependencies ++= Seq(
  "org.typelevel"               %% "cats"                  % "0.9.0",
  "com.typesafe.akka"           %% "akka-http"             % "10.0.10",
  "com.typesafe.akka"           %% "akka-http-spray-json"  % "10.0.10",
  "net.sf.py4j"                 %  "py4j"                  % "0.10.5",
  "org.apache.spark"            %% "spark-core"            % "2.2.0" % "provided",
  "org.apache.commons"          % "commons-math3"          % "3.6.1",
  "org.locationtech.geotrellis" %% "geotrellis-s3"         % Version.geotrellis,
  "org.locationtech.geotrellis" %% "geotrellis-s3-testkit" % Version.geotrellis,
  "org.locationtech.geotrellis" %% "geotrellis-spark"      % Version.geotrellis,
  "org.locationtech.geomesa"    %% "geomesa-spark-core"    % Version.geomesa
)

assemblyShadeRules in assembly := {
  val shadePackage = "org.locationtech.geopyspark.shaded"
  Seq(
    ShadeRule.rename("org.apache.avro.**" -> s"$shadePackage.org.apache.avro.@1")
      .inLibrary("org.locationtech.geotrellis" %% "geotrellis-spark" % Version.geotrellis).inAll,
    ShadeRule.rename("com.typesafe.scalalogging.**" -> s"$shadePackage.com.typesafe.scalalogging.@1")
      .inLibrary("org.locationtech.geotrellis" %% "geotrellis-spark" % Version.geotrellis).inAll
  )
}

assemblyMergeStrategy in assembly := {
  case "reference.conf" => MergeStrategy.concat
  case "application.conf" => MergeStrategy.concat
  case "META-INF/MANIFEST.MF" => MergeStrategy.discard
  case "META-INF\\MANIFEST.MF" => MergeStrategy.discard
  case "META-INF/ECLIPSEF.RSA" => MergeStrategy.discard
  case "META-INF/ECLIPSEF.SF" => MergeStrategy.discard
  case x if x.startsWith("META-INF/services") => MergeStrategy.concat
  case _ => MergeStrategy.first
}

PB.targets in Compile := Seq(
  scalapb.gen() -> (sourceManaged in Compile).value
)
