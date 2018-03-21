GeoPySpark
**********
.. image:: https://travis-ci.org/locationtech-labs/geopyspark.svg?branch=master
   :target: https://travis-ci.org/locationtech-labs/geopyspark

.. image:: https://readthedocs.org/projects/geopyspark/badge/?version=latest
   :target: https://geopyspark.readthedocs.io/en/latest/?badge=latest


GeoPySpark is a Python bindings library for `GeoTrellis <http://geotrellis.io>`_ and
`GeoMesa <http://geomesa.org>`_. GeoTrellis and GeoMesa together form a complete
GeoSpatial analytics platform for working with distributed geospatial data. By
using `PySpark <http://spark.apache.org/docs/latest/api/python/pyspark.html>`_,
GeoPySpark is able to provide an interface into the GeoTrellis and GeoMesa frameworks.

A Quick Example
---------------

Here is a quick example of GeoPySpark. In the following code, we take NLCD data
of the state of Pennsylvania from 2011, and do a masking operation on it with
a Polygon that represents an area of interest. This masked layer is then saved.

If you wish to follow along with this example, you will need to download the
NLCD data and unzip it. Running these two commands will complete these tasks
for you:

.. code:: console

   curl -o /tmp/NLCD2011_LC_Pennsylvannia.zip https://s3-us-west-2.amazonaws.com/prd-tnm/StagedProducts/NLCD/2011/landcover/states/NLCD2011_LC_Pennsylvania.zip?ORIG=513_SBDDG
   unzip -d /tmp /tmp/NLCD2011_LC_Pennsylvannia.zip

.. code:: python

  import geopyspark as gps

  from pyspark import SparkContext
  from shapely.geometry import box


  # Create the SparkContext
  conf = gps.geopyspark_conf(appName="geopyspark-example", master="local[*]")
  sc = SparkContext(conf=conf)

  # Read in the NLCD tif that has been saved locally.
  # This tif represents the state of Pennsylvania.
  raster_layer = gps.geotiff.get(layer_type=gps.LayerType.SPATIAL,
                                 uri='/tmp/NLCD2011_LC_Pennsylvania.tif',
                                 num_partitions=100)

  # Tile the rasters within the layer and reproject them to Web Mercator.
  tiled_layer = raster_layer.tile_to_layout(layout=gps.GlobalLayout(), target_crs=3857)

  # Creates a Polygon that covers roughly the north-west section of Philadelphia.
  # This is the region that will be masked.
  area_of_interest = box(-75.229225, 40.003686, -75.107345, 40.084375)

  # Mask the tiles within the layer with the area of interest
  masked = tiled_layer.mask(geometries=area_of_interest)

  # We will now pyramid the masked TiledRasterLayer so that we can use it in a TMS server later.
  pyramided_mask = masked.pyramid()

  # Save each layer of the pyramid locally so that it can be accessed at a later time.
  for pyramid in pyramided_mask.levels.values():
      gps.write(uri='file:///tmp/pa-nlcd-2011',
                layer_name='north-west-philly',
                tiled_raster_layer=pyramid)


Contact and Support
-------------------

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
-----

GeoPySpark Requirements
^^^^^^^^^^^^^^^^^^^^^^^

============ ============
Requirement  Version
============ ============
Java         >=1.8
Scala        >=2.11
Python       3.3 - 3.6
Spark        >=2.1.1
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
^^^^^^^^^^^^^^

Before installing, check the above table to make sure that the
requirements are met.

Installing From Pip
~~~~~~~~~~~~~~~~~~~

To install via ``pip`` open the terminal and run the following:

.. code:: console

   pip install geopyspark
   geopyspark install-jar -p [path/to/install/jar]

Where the first command installs the python code from PyPi and the second
downloads the backend, jar file. If no path is given when downloading the jar,
then it will be downloaded to wherever GeoPySpark was installed at.

What's With That Weird Pip Install?
===================================

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
~~~~~~~~~~~~~~~~~~~~~~

If you would rather install from source, clone the GeoPySpark repo and enter it.

.. code:: console

   git clone https://github.com/locationtech-labs/geopyspark.git
   cd geopyspark

Installing For Users
====================

.. code:: console

   make install

This will assemble the backend-end ``jar`` that contains the Scala code,
move it to the ``jars`` sub-package, and then runs the ``setup.py`` script.

Note:
  If you have altered the global behavior of ``sbt`` this install may
  not work the way it was intended.

Installing For Developers
=========================

.. code:: console

   make build
   pip install -e .

``make build`` will assemble the back-end ``jar`` and move it the ``jars``
sub-package. The second command will install GeoPySpark in "editable" mode.
Meaning any changes to the source files will also appear in your system
installation.

Installing to a Virtual Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
====================

.. code:: console

   make virtual-install

Installing For Developers
=========================

.. code:: console

   make build
   pip install -e .


Developing GeoPySpark With GeoNotebook
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Note**: Before beginning this section, it should be noted that python-mapnik,
a dependency for GeoNotebook, has been found to be difficult to install. If
problems are encountered during installation, a possible work around would be
to run ``make wheel`` and then do ``docker cp`` the ``wheel`` into the
GeoPySpark docker container and install it from there.

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
~~~~~~~~~~~~~~~~~~~~~~~~

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


Running GeoPySpark Tests
------------------------

GeoPySpark uses the `pytest <https://docs.pytest.org/en/latest/>`_ testing
framework to run its unittests. If you wish to run GeoPySpark's unittests,
then you must first clone this repository to your machine. Once complete,
go to the root of the library and run the following command:

.. code:: console

   pytest

This will then run all of the tests present in the GeoPySpark library.

**Note**: The unittests require additional dependencies in order to pass fully.
`pyrproj <https://pypi.python.org/pypi/pyproj?>`_, `colortools <https://pypi.python.org/pypi/colortools/0.1.2>`_,
and `matplotlib <https://pypi.python.org/pypi/matplotlib/2.0.2>`_  (only for >=Python3.4) are needed to
ensure that all of the tests pass.

Make Targets
^^^^^^^^^^^^

 - **install** - install GeoPySpark python package locally
 - **wheel** - build python GeoPySpark wheel for distribution
 - **pyspark** - start pyspark shell with project jars
 - **build** - builds the backend jar and moves it to the jars sub-package
 - **clean** - remove the wheel, the backend jar file, and clean the
   geotrellis-backend directory

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
