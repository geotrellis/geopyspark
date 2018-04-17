#!/usr/bin/env bash

set -e
set -x

aws s3 cp geopyspark/jars/geotrellis-backend-assembly-*.jar s3://geopyspark-dependency-jars/ \
  && python3 setup.py bdist_egg bdist_wheel \
  && aws s3 cp dist/geopyspark*.egg s3://geopyspark-dependency-jars/ \
  && aws s3 cp dist/geopyspark*.whl s3://geopyspark-dependency-jars/ \
  && cd geopyspark-backend \
  && ./sbt -Dbintray.user=$BINTRAY_USER -Dbintray.pass=$BINTRAY_PASS "project geotrellis-backend" publish \
  && ./sbt -Dbintray.user=$BINTRAY_USER -Dbintray.pass=$BINTRAY_PASS "project vectorpipe" publish \
  && ./sbt -Dbintray.user=$BINTRAY_USER -Dbintray.pass=$BINTRAY_PASS "project geotools" publish
