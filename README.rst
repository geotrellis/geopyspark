GeoPySpark
***********
.. image:: https://travis-ci.org/locationtech-labs/geopyspark.svg?branch=master
   :target: https://travis-ci.org/locationtech-labs/geopyspark

.. image:: https://readthedocs.org/projects/geopyspark/badge/?version=latest
   :target: https://geopyspark.readthedocs.io/en/latest/?badge=latest

``GeoPySpark`` provides Python bindings for working with geospatial data using `PySpark <http://spark.apache.org/docs/latest/api/python/pyspark.html>`_.
It will provide interfaces into GeoTrellis and GeoMesa LocationTech frameworks.
It is currently under development, and has just entered alpha.

Currently, only functionality from GeoTrellis has been supported. GeoMesa
LocationTech frameworks will be added at a later date.

A Quick Example
----------------

Here is a quick example of GeoPySpark. In the following code, we take NLCD data
of the state of Pennsylvania from 2011, and do a polygonal summary of an area
of interest to find the min and max classifications values of that area.

If you wish to follow along with this example, you will need to download the
NLCD data and the geojson that represents the area of interest. Running these
two commands will download these files for you:

.. code:: console

   curl -o /tmp/NLCD2011_LC_Pennsylvannia.zip https://s3-us-west-2.amazonaws.com/prd-tnm/StagedProducts/NLCD/2011/landcover/states/NLCD2011_LC_Pennsylvania.zip?ORIG=513_SBDDG
   unzip /tmp/NLCD2011_LC_Pennsylvannia.zip
   curl -o /tmp/area_of_interest.geojson https://s3.amazonaws.com/geopyspark-test/area_of_interest.json

.. code:: python

  import json
  from functools import partial

  from geopyspark.geotrellis.constants import SPATIAL, ZOOM
  from geopyspark.geotrellis.geotiff_rdd import get
  from geopyspark.geotrellis.catalog import write

  from pyspark import SparkContext

  from shapely.geometry import Polygon, shape
  from shapely.ops import transform
  import pyproj


  # Create the SparkContext
  pysc = SparkContext(appName="example", master="local[*]")

  # Read in the NLCD tif that has been saved locally.
  # This tif represents the state of Pennsylvania.
  raster_rdd = get(pysc=pysc, rdd_type=SPATIAL,
  uri='/tmp/NLCD2011_LC_Pennsylvania.tif',
  options={'numPartitions': 100})

  tiled_rdd = raster_rdd.to_tiled_layer()

  # Reproject the reclassified TiledRasterRDD so that it is in WebMercator
  reprojected_rdd = tiled_rdd.reproject(3857, scheme=ZOOM).cache().repartition(150)

  # We will do a polygonal summary of the north-west region of Philadelphia.
  with open('/tmp/area_of_interest.json') as f:
      txt = json.load(f)

  geom = shape(txt['features'][0]['geometry'])

  # We need to reporject the geometry to WebMercator so that it will intersect with
  # the TiledRasterRDD.
  project = partial(
      pyproj.transform,
      pyproj.Proj(init='epsg:4326'),
      pyproj.Proj(init='epsg:3857'))

  area_of_interest = transform(project, geom)

  # Find the min and max of the values within the area of interest polygon.
  min_val = reprojected_rdd.polygonal_min(geometry=area_of_interest, data_type=int)
  max_val = reprojected_rdd.polygonal_max(geometry=area_of_interest, data_type=int)

  print('The min value of the area of interest is:', min_val)
  print('The max value of the area of interest is:', max_val)

  # We will now pyramid the relcassified TiledRasterRDD so that we can use it in a TMS server later.
  pyramided_rdd = reprojected_rdd.pyramid(start_zoom=1, end_zoom=12)

  # Save each layer of the pyramid locally so that it can be accessed at a later time.
  for pyramid in pyramided_rdd:
      write('file:///tmp/nld-2011', 'pa', pyramid)


Contact and Support
--------------------

If you need help, have questions, or like to talk to the developers (let us
know what you're working on!) you contact us at:

 * `Gitter <https://gitter.im/geotrellis/geotrellis>`_
 * `Mailing list <https://locationtech.org/mailman/listinfo/geotrellis-user>`_

As you may have noticed from the above links, those are links to the GeoTrellis
gitter channel and mailing list. This is because this project is currently an
offshoot of GeoTrellis, and we will be using their mailing list and gitter
channel as a means of contact. However, we will form our own if there is a need
for it.

Setup
------

GeoPySpark Requirements
^^^^^^^^^^^^^^^^^^^^^^^^

============ ============
Requirement  Version
============ ============
Java         >=1.8
Scala        2.11.8
Python       3.3 - 3.5
Hadoop       >=2.0.1
============ ============

Java 8 and Scala 2.11 are needed for GeoPySpark to work; as they are required by
GeoTrellis. In addition, Spark needs to be installed and configured with the
environment variable, ``SPARK_HOME`` set.

You can test to see if Spark is installed properly by running the following in
the terminal:

.. code:: console

   > echo $SPARK_HOME
   /usr/local/bin/spark

If the return is a path leading to your Spark folder, then it means that Spark
has been configured correctly.

How to Install
^^^^^^^^^^^^^^^

Before installing, check the above table to make sure that the
requirements are met.

Installing From Pip
~~~~~~~~~~~~~~~~~~~~

To install via ``pip`` open the terminal and run the following:

.. code:: console

   pip install geopyspark
   geopyspark install-jar -p [path/to/install/jar]

Where the first command installs the python code from PyPi and the second
downloads the backend, jar file. If no path is given when downloading the jar,
then it will be downloaded to wherever GeoPySpark was installed at.

What's With That Weird Pip Install?
====================================

"What's with that weird pip install?", you may be asking yourself. The reason
for its unusualness is due to how GeoPySpark functions. Because this library
is a python binding for a Scala project, we need to be able to access the
Scala backend. To do this, we plug into PySpark which acts as a bridge between
Python and Scala. However, in order to achieve this the Scala code needs to be
assembled into a jar file. This poses a problem due to its size (117.7 MB at
v0.1.0-RC!). To get around the size constraints of PyPi, we thus utilized this
method of distribution where the jar must be downloaded in a separate command
when using ``pip install``.

Note:
  Installing from source or for development does not require the separate
  download of the jar.

Installing From Source
~~~~~~~~~~~~~~~~~~~~~~~

If you would rather install from source, clone the GeoPySpark repo and enter it.

.. code:: console

   git clone https://github.com/locationtech-labs/geopyspark.git
   cd geopyspark

Installing For Users
=====================

.. code:: console

   make install

This will assemble the backend-end ``jar`` that contains the Scala code,
move it to the ``jars`` sub-package, and then runs the ``setup.py`` script.

Note:
  If you have altered the global behavior of ``sbt`` this install may
  not work the way it was intended.

Installing For Developers
===========================

.. code:: console

   make build
   pip install -e .

``make build`` will assemble the back-end ``jar`` and move it the ``jars``
sub-package. The second command will install GeoPySpark in "editable" mode.
Meaning any changes to the source files will also appear in your system
installation.

Installing to a Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A third option is to install GeoPySpark in a virtual environment. To get things
started, enter the environment and run the following:

.. code:: console

   git clone https://github.com/locationtech-labs/geopyspark.git
   cd geopyspark
   export PYTHONPATH=$VIRTUAL_ENV/lib/<your python version>/site-packages

Replace ``<your python version`` with whatever Python version
``virtualenvwrapper`` is set to. Installation in a virtual environment can be
a bit weird with GeoPySpark. This is why you need to export the
``PYTHONPATH`` before installing to ensure that it performs correctly.

Installing For Users
=====================

.. code:: console

   make virtual-install

Installing For Developers
===========================

.. code:: console

   make build
   pip install -e .


Developing GeoPySpark With GeoNotebook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`GeoNotebook <https://github.com/OpenGeoscience/geonotebook>`_ is a Jupyter
notebook extension that specializes in working with geospatial data. GeoPySpark
can be used with this notebook; which allows for a more interactive experience
when using the library. For this section, we will be installing both tools in a
virtual environment. It is recommended that you start with a new environment
before following this guide.

Because there's already documentation on how to install GeoPySpark in a virtual
environment, we won't go over it here. As for GeoNotebook, it also has a section
on `installation <https://github.com/OpenGeoscience/geonotebook#make-a-virtualenv-install-jupyternotebook-install-geonotebook>`_
so that will not be covered here either.

Once you've setup both GeoPySpark and GeoNotebook, all that needs to be done
is go to where you want to save/have saved your notebooks and execute this
command:

.. code:: console

   jupyter notebook

This will open up the jupyter hub and will allow you to work on your notebooks.

It is also possible to develop with both GeoPySpark and GeoNotebook in editable mode.
To do so you will need to re-install and re-register GeoNotebook with Jupyter.

.. code:: console

   pip uninstall geonotebook
   git clone --branch feature/geotrellis https://github.com/geotrellis/geonotebook ~/geonotebook
   pip install -r ~/geonotebook/prerequirements.txt
   pip install -r ~/geonotebook/requirements.txt
   pip install -e ~/geonotebook
   jupyter serverextension enable --py geonotebook
   jupyter nbextension enable --py geonotebook
   make notebook

The default ``Geonotebook (Python 3)`` kernel will require the following environment variables to be defined:

.. code:: console

   export PYSPARK_PYTHON="/usr/local/bin/python3"
   export SPARK_HOME="/usr/local/apache-spark/2.1.1/libexec"
   export PYTHONPATH="${SPARK_HOME}/python/lib/py4j-0.10.4-src.zip:${SPARK_HOME}/python/lib/pyspark.zip"

Make sure to define them to values that are correct for your system.
The ``make notebook`` command also makes used of ``PYSPARK_SUBMIT_ARGS`` variable defined in the ``Makefile``.

GeoNotebook/GeoTrellis integration in currently in active development and not part of GeoNotebook master.
The latest development is on a ``feature/geotrellis`` branch at ``<https://github.com/geotrellis/geonotebook>``.

Side Note For Developers
~~~~~~~~~~~~~~~~~~~~~~~~~

An optional (but recommended!) step for developers is to place these
two lines of code at the top of your notebooks.

.. code:: console

   %load_ext autoreload
   %autoreload 2

This will make it so that you don't have to leave the notebook for your changes
to take affect. Rather, you just have to reimport the module and it will be
updated. However, there are a few caveats when using ``autoreload`` that can be
read `here <http://ipython.readthedocs.io/en/stable/config/extensions/autoreload.html#caveats>`_.

Using ``pip install -e`` in conjunction with ``autoreload`` should cover any
changes made, though, and will make the development experience much less
painful.

GeoPySpark Script
-----------------

When GeoPySpark is installed, it comes with a script which can be accessed
from anywhere on you computer. These are the commands that can be ran via the
script:

.. code:: console

   geopyspark install-jar -p, --path [download/path] //downloads the jar file
   geopyspark jar-path //returns the relative path of the jar file
   geopyspark jar-path -a, --absolute //returns the absolute path of the jar file

The first command is only needed when installing GeoPySpark through ``pip``;
and it **must** be ran before using GeoPySpark. If no path is selected, then
the jar will be installed wherever GeoPySpark was installed.

The second and third commands are for getting the location of the jar file.
These can be used regardless of installation method. However, if installed
through ``pip``, then the jar must be downloaded first or these commands
will not work.

Make Targets
^^^^^^^^^^^^

 - **install** - install GeoPySpark python package locally
 - **wheel** - build python GeoPySpark wheel for distribution
 - **pyspark** - start pyspark shell with project jars
 - **build** - builds the backend jar and moves it to the jars sub-package
 - **docker-build** - build docker image for Jupyter with GeoPySpark
 - **clean** - remove the wheel, the backend jar file, and clean the
   geotrellis-backend directory
 - **cleaner** - the same as **clean**, but also erase all .pyc
   files and delete binary artifacts in the docker directory

Docker Container
^^^^^^^^^^^^^^^^

To build the docker container, type the following in a terminal:

.. code:: console

   make docker-build

If you encounter problems, typing ``make cleaner`` before typing
``make docker-build`` could help.

To run the container, type:

.. code:: console

   docker run -it --rm -p 8000:8000 quay.io/geodocker/jupyter-geopyspark:6

Uninstalling
------------

To uninstall GeoPySpark, run the following in the terminal:

.. code:: console

   pip uninstall geopyspark
   rm .local/bin/geopyspark

Contributing
------------

Any kind of feedback and contributions to GeoPySpark is always welcomed.
A CLA is required for contribution, see `Contributing <docs/contributing.rst>`_ for more
information.
