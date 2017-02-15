lazy val commonSettings = Seq(
  version := Version.geopyspark,
  scalaVersion := Version.scala,
  crossScalaVersions := Version.crossScala,
  description := "GeoPySpark Demo",
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


lazy val root = Project("root", file(".")).
  dependsOn(geotrellisProject)

lazy val geotrellisProject = Project("geotrellis-backend", file("geotrellis")).
  settings(commonSettings: _*)
