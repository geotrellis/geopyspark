export PYTHON := python3
export PYSPARK_PYTHON := ipython
export ASSEMBLED="assembled"

rwildcard=$(foreach d,$(wildcard $1*),$(call rwildcard,$d/,$2) $(filter $(subst *,%,$2),$d))

GPS-VERSION := 0.3.0.gm.2
JAR-PATH := geopyspark/jars

ASSEMBLYNAME := geopyspark-assembly-${GPS-VERSION}.jar
BUILD-ASSEMBLY := geopyspark-backend/geopyspark/target/scala-2.11/${ASSEMBLYNAME}
DIST-ASSEMBLY := ${JAR-PATH}/${ASSEMBLYNAME}

WHEELNAME := geopyspark-${GPS-VERSION}-py3-none-any.whl
WHEEL := dist/${WHEELNAME}

SCALA_SRC := $(call rwildcard, geopyspark-backend/geopyspark/src/, *.scala)
SCALA_BLD := $(wildcard geopyspark-backend/project/*) geopyspark-backend/build.sbt geopyspark-backend/geopyspark/build.sbt
PYTHON_SRC := $(call rwildcard, geopyspark/, *.py)

export PYSPARK_SUBMIT_ARGS := --master local[*] --driver-memory 8G --jars ${PWD}/${DIST-ASSEMBLY} \
--conf spark.serializer=org.apache.spark.serializer.KryoSerializer pyspark-shell


install: ${DIST-ASSEMBLY} ${WHEEL}
	${PYTHON} setup.py install --user --force --prefix=

virtual-install: ${DIST-ASSEMBLY}
	pip install -r requirements.txt --force && \
	${PYTHON} setup.py install --force

${DIST-ASSEMBLY}: ${BUILD-ASSEMBLY}
	cp -f ${BUILD-ASSEMBLY} ${DIST-ASSEMBLY}

${BUILD-ASSEMBLY}: ${SCALA_SRC} ${SCALA_BLD}
	(cd geopyspark-backend && ./sbt "project geopyspark" assembly)

${WHEEL}: ${DIST-ASSEMBLY} ${PYTHON_SRC} setup.py
	rm -rf build/
	${PYTHON} setup.py bdist_wheel

wheel: ${WHEEL}

build: clean ${DIST-ASSEMBLY}

pyspark: ${DIST-ASSEMBLY}
	pyspark --jars ${DIST-ASSEMBLY} \
		--conf spark.serializer=org.apache.spark.serializer.KryoSerializer \
		--conf spark.kyro.registrator=geopyspark.geotools.kryo.ExpandedKryoRegistrator

jupyter: ${DIST-ASSEMBLY}
	@echo "PYSPARK_PYTHON: $${PYSPARK_PYTHON}"
	@echo "SPARK_HOME: $${SPARK_HOME}"
	@echo "PYTHONPATH: $${PYTHONPATH}"
	@echo "PYSPARK_SUBMIT_ARGS: $${PYSPARK_SUBMIT_ARGS}"
	jupyter notebook --port 8000 --notebook-dir notebooks/

clean:
	rm -f ${WHEEL} ${DIST-ASSEMBLY}
	(cd geopyspark-backend && ./sbt "project geopyspark" clean)
