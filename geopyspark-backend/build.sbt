lazy val commonSettings = Seq(
  version := Version.geopyspark + scala.util.Properties.envOrElse("GEOPYSPARK_VERSION_SUFFIX", ""),
  scalaVersion := Version.scala,
  description := "GeoPySpark",
  organization := "org.locationtech.geotrellis",
  licenses := Seq("Apache-2.0" -> url("http://www.apache.org/licenses/LICENSE-2.0.html")),
  scalacOptions ++= Seq(
    "-deprecation",
    "-unchecked",
    "-Yinline-warnings",
    "-language:implicitConversions",
    "-language:reflectiveCalls",
    "-language:higherKinds",
    "-language:postfixOps",
    "-language:existentials",
    "-feature"),

  shellPrompt := { s => Project.extract(s).currentProject.id + " > " },

  externalResolvers := Seq(
    "Geotoolkit Repo" at "http://maven.geotoolkit.org",
    "OSGeo GeoTools" at "http://download.osgeo.org/webdav/geotools/",
    "geosolutions" at "http://maven.geo-solutions.it/",
    "LocationTech Snapshots" at "https://repo.locationtech.org/content/groups/snapshots",
    "LocationTech Releases" at "https://repo.locationtech.org/content/groups/releases",
    Resolver.bintrayRepo("azavea", "maven"),
    DefaultMavenRepository
  ),

  addCompilerPlugin("org.spire-math" % "kind-projector" % "0.9.3" cross CrossVersion.binary),
  addCompilerPlugin("org.scalamacros" %% "paradise" % "2.1.0" cross CrossVersion.full)
)

lazy val publishSettings =
  Seq(
    bintrayOrganization := Some("azavea"),
    bintrayRepository := "maven",
    bintrayVcsUrl := Some("https://github.com/locationtech-labs/geopyspark.git"),
    publishMavenStyle := true,
    publishArtifact in Test := false,
    pomIncludeRepository := { _ => false},
    homepage := Some(url("https://github.com/locationtech-labs/geopyspark"))
  )



scalaVersion := Version.scala
scalaVersion in ThisBuild := Version.scala

lazy val root = Project("root", file("."))

lazy val utilProject = Project("util", file("util"))
  .settings(commonSettings: _*)
  .settings(publishSettings: _*)

lazy val vectorPipeProject = Project("vectorpipe", file("vectorpipe"))
  .settings(commonSettings: _*)
  .settings(publishSettings: _*)
  .dependsOn(utilProject)

lazy val geotoolsProject = Project("geotools", file("geotools"))
  .settings(commonSettings: _*)
  .settings(publishSettings: _*)
  .dependsOn(utilProject)

lazy val geotrellisProject = Project("geotrellis-backend", file("geotrellis"))
  .settings(commonSettings: _*)
  .settings(publishSettings: _*)
  .dependsOn(utilProject, vectorPipeProject)

lazy val geopysparkProject = Project("geopyspark", file("geopyspark"))
  .settings(commonSettings: _*)
  .settings(publishSettings: _*)
  .dependsOn(utilProject, vectorPipeProject, geotoolsProject, geotrellisProject)
