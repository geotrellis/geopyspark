lazy val commonSettings = Seq(
  version := Version.geopyspark,
  scalaVersion := Version.scala,
  crossScalaVersions := Version.crossScala,
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

  resolvers += Resolver.sonatypeRepo("releases"),

  addCompilerPlugin("org.spire-math" % "kind-projector" % "0.9.3" cross CrossVersion.binary),
  addCompilerPlugin("org.scalamacros" %% "paradise" % "2.1.0" cross CrossVersion.full)
)

resolvers ++= Seq(
  "Location Tech GeoTrellis Snapshots" at "https://repo.locationtech.org/content/repositories/geotrellis-snapshots",
  Resolver.mavenLocal
)

scalaVersion := Version.scala

lazy val root = Project("root", file("."))

lazy val utilProject = Project("util", file("util"))
  .settings(commonSettings: _*)
  .dependsOn(root)

lazy val vectorPipeProject = Project("vectorpipe", file("vectorpipe"))
  .settings(commonSettings: _*)
  .dependsOn(root, utilProject)

lazy val geotrellisProject = Project("geotrellis-backend", file("geotrellis"))
  .settings(commonSettings: _*)
  .dependsOn(root, utilProject, vectorPipeProject)
