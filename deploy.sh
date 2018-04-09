#!/usr/bin/env bash

set -e
set -x

aws s3 cp geopyspark/jars/geopyspark-assembly-*.jar s3://geopyspark-dependency-jars/ \
  && cd geopyspark-backend \
  && ./sbt -Dbintray.user=$BINTRAY_USER -Dbintray.pass=$BINTRAY_PASS "project geotrellis-backend" publish \
  && ./sbt -Dbintray.user=$BINTRAY_USER -Dbintray.pass=$BINTRAY_PASS "project vectorpipe" publish \
  && ./sbt -Dbintray.user=$BINTRAY_USER -Dbintray.pass=$BINTRAY_PASS "project geotools" publish
