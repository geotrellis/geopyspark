export PYTHON := python3
export PYSPARK_PYTHON := ipython
export ASSEMBLED="assembled"

JAR-PATH := geopyspark/jars
ASSEMBLYNAME := geotrellis-backend-assembly-0.1.0.jar
BUILD-ASSEMBLY := geopyspark-backend/geotrellis/target/scala-2.11/${ASSEMBLYNAME}
DIST-ASSEMBLY := ${JAR-PATH}/${ASSEMBLYNAME}
WHEELNAME := geopyspark-0.1.0-py3-none-any.whl
WHEEL := dist/${WHEELNAME}
rwildcard=$(foreach d,$(wildcard $1*),$(call rwildcard,$d/,$2) $(filter $(subst *,%,$2),$d))

install: ${DIST-ASSEMBLY} ${WHEEL}
	${PYTHON} setup.py install --user --force --prefix=

${DIST-ASSEMBLY}: ${BUILD-ASSEMBLY}
	cp -f ${BUILD-ASSEMBLY} ${DIST-ASSEMBLY}

${BUILD-ASSEMBLY}: $(call rwildcard, geopyspark-backend/, *.scala)
	(cd geopyspark-backend && ./sbt "project geotrellis-backend" assembly)

${WHEEL}: ${DIST-ASSEMBLY} $(call rwildcard, geopyspark, *.py) setup.py
	${PYTHON} setup.py bdist_wheel

wheel: ${WHEEL}

pyspark: ${DIST-ASSEMBLY}
	pyspark --jars ${DIST-ASSEMBLY} \
		--conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
		--conf spark.kyro.registrator=geotrellis.spark.io.kyro.KryoRegistrator

docker/archives/${ASSEMBLYNAME}: ${DIST-ASSEMBLY}
	cp -f ${DIST-ASSEMBLY} docker/archives/${ASSEMBLYNAME}

docker/archives/${WHEELNAME}: ${WHEEL}
	cp -f ${WHEEL} docker/archives/${WHEELNAME}

docker-build: docker/archives/${ASSEMBLYNAME} docker/archives/${WHEELNAME}
	(cd docker && make)

docker-run:
	(cd docker && make run)

clean:
	rm -f ${WHEEL} ${DIST-ASSEMBLY}
	(cd geopyspark-backend && ./sbt "project geotrellis-backend" clean)
	(cd docker && make clean)

cleaner: clean
	rm -f `find ./build ./geopyspark | grep "\.pyc"`
	(cd docker && make cleaner)

cleanest: cleaner
	(cd docker && make cleanest)
