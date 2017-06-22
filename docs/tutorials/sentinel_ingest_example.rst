.. _sentinel_ingest_example:

Ingesting a Sentinel Image
***************************

Sentinel-2 is an observation mission developed by the European Space Agency to
monitor the surface of the Earth (`official website
<http://www.esa.int/Our_Activities/Observing_the_Earth/Copernicus/Sentinel-2>`_).
Sets of images are taken of the surface where each image corresponds to a
specific wavelength. These images can provide useful data for a wide variety of
industries, however, the format they are stored can prove difficult to work
with. This being, ``JPEG 2000`` (file extension ``.jp2``), an image compression
format for JPEGs that allow for improved quality and compression ratio.

There are few programs that can work with ``jp2``, which can make processing
large amounts of them difficult. Because of GeoPySpark, though, we can leverage
the tools available to us in Python that can work with ``jp2`` and use them to
format the sentinel data so that it can be ingested.

**Note**: This guide goes over how to use ``jp2`` files with GeoPySpark, the
actual ingest process itself is discussed in more detail in
:ref:`Greyscale Ingest Code Breakdown <break_down>`.


Getting the Data
================

Before we can start this tutorial, we will need to get the sentinel images.
All sentinel data can be found on Amazon's S3, and we will be downloading it
straight from there.

The way the data is stored on S3 will not be discussed here, instead, a general
overview of the data will be given. We will downloading three different ``jp2``
that represent the same area and time in different wavelength. These being:
Aerosol detection (443 nm), Water vapor (945 nm), and Cirrus (1375 nm). Why
these three bands? It's because of the resolution of the image, which
determines what bands are represented best. For this example, we will be
working at a 60 m resolution; which provides the best representation of the
mentioned bands. As for what is in the photos, it is the eastern coast of
Corsica taken on January 4th, 2017.

All of the above helps create the following base url for this image set, which we
will assign to the ``baseurl`` variable in the terminal:

.. code:: console

  baseurl="http://sentinel-s2-l1c.s3.amazonaws.com/tiles/32/T/NM/2017/1/4/0/"


To download the bands, we just have to ``wget`` each one, and then move the
resulting ``jp2`` to ``/tmp``.

.. code:: console

 wget ${baseurl}B01.jp2 ${baseurl}B09.jp2 ${baseurl}B10.jp2
 mv B01.jp2 B09.jp2 B10.jp2 /tmp


Now that we have our data, we can now begin the ingest process.


The Code
=========

.. code:: python

  import rasterio
  import numpy as np

  from geopyspark.geotrellis.constants import SPATIAL, ZOOM
  from geopyspark.geotrellis.catalog import write
  from geopyspark.geotrellis.rdd import RasterRDD

  from pyspark import SparkContext


  pysc = SparkContext(appName="sentinel-ingest", master="local[*]")

  jp2s = ["/tmp/B01.jp2", "/tmp/B09.jp2", "/tmp/B10.jp2"]
  arrs = []

  # Reading the jp2s with rasterio
  for jp2 in jp2s:
      with rasterio.open(jp2) as f:
          arrs.append(f.read(1))

  data = np.array(arrs, dtype=arrs[0].dtype)

  # saving the max and min values of the tile with
  open('/tmp/sentinel_stats.txt', 'w') as f:
      f.writelines([str(data.max()) + "\n", str(data.min())])

  if f.nodata:
      no_data = f.nodata
  else:
      no_data = 0

  bounds = f.bounds
  epsg_code = int(f.crs.to_dict()['init'][5:])

  # Creating the RasterRDD
  tile = {'data': data, 'no_data_value': no_data}

  extent = {'xmin': bounds.left, 'ymin': bounds.bottom, 'xmax': bounds.right, 'ymax': bounds.top}
  projected_extent = {'extent': extent, 'epsg': epsg_code}

  rdd = pysc.parallelize([(projected_extent, tile)])
  raster_rdd = RasterRDD.from_numpy_rdd(pysc, SPATIAL, rdd)

  metadata = raster_rdd.collect_metadata()
  laid_out = raster_rdd.tile_to_layout(metadata)
  reprojected = laid_out.reproject("EPSG:3857", scheme=ZOOM)

  pyramided = reprojected.pyramid(start_zoom=12, end_zoom=1)

  for tiled in pyramided:
      write("file:///tmp/sentinel-catalog", "sentinel-benchmark", tiled)


Running the Code
-----------------

Running the code is simple, and you have two different ways of doing it.

The first is to copy and paste the code into a console like, iPython, and then
running it.

The second is to place this code in a python file and then saving it. To run it
from the file, go to the directory the file is in and run this command:

.. code-block:: none

  python3 file.py

Just replace ``file.py`` with whatever name you decided to call the file.


Breaking Down the Code
=======================

Let's now see what's going on through the code by going through each step of
the process. **Note**: As mentioned in the opening, this section will only
cover the reading in and formatting the data steps. For a guide through each
ingest step, please see :ref:`Greyscale Ingest Code Breakdown <break_down>`.


The Imports
------------

The one note to make here is:

.. code-block:: python

  import rasterio
  import numpy as np

We will need ``rasterio`` to read in the `jp2`` and ``numpy`` to format the
data so that it can be used with GeoPySpark.


Reading in the JPEG 2000s
--------------------------

.. code-block:: python

  jp2s = ["/tmp/B01.jp2", "/tmp/B09.jp2", "/tmp/B10.jp2"]
  arrs = []

  # Reading the jp2s with rasterio
  for jp2 in jp2s:
      with rasterio.open(jp2) as f:
          arrs.append(f.read(1))

  data = np.array(arrs, dtype=arrs[0].dtype)


``rasterio`` being backed by GDAL allows us to read in the ``jp2``.
Because each image represents a wavelength, there is a order in which
they need to be in when they're merged to together into a multiband raster which
is represented by ``jp2s``. After the reading process, the list of ``numpy``
arrays will be turned into one array. This represents our mulitband raster.


Saving the Whole Image Stats
-----------------------------

.. code-block:: python

  # saving the max and min values of the tile with
  open('/tmp/sentinel_stats.txt', 'w') as f:
      f.writelines([str(data.max()) + "\n", str(data.min())])

When we create the tile server for our sentinel images, the data of the
``numpy`` arrays will need to be converted to the ``uint8`` data type in order
to be represented as a RGB image. In order to do that, though, we will need to
normalize each array so that all of the points fall between 0 and 255. This
posss a problem, since only a section of the original image is read in and
rendered at a time, there is no way of normalizing correctly; as we do not know
the entire range of values from the original image. This is why we must save the
``max`` and ``min`` values of the whole image in a seperate file to read in later.


Formatting the Data
--------------------

.. code-block:: python

  if f.nodata:
      no_data = f.nodata
  else:
      no_data = 0

  bounds = f.bounds
  epsg_code = int(f.crs.to_dict()['init'][5:])

  extent = {'xmin': bounds.left, 'ymin': bounds.bottom, 'xmax': bounds.right, 'ymax': bounds.top}
  projected_extent = {'extent': extent, 'epsg': epsg_code}

  rdd = pysc.parallelize([(projected_extent, tile)])
  raster_rdd = RasterRDD.from_numpy_rdd(pysc, SPATIAL, rdd)


GeoPySpark is a Python binding of GeoTrellis, and because of that, requires the
data to be in a certain format. Please see
:ref:`core_concepts` to learn what each of these variables represent.

The main take-away from this section of code: if you wish to
produce either a ``RasterRDD`` or ``TiledRasterRDD`` in Python, then the data
**must** be in the correct format.


Ingesting the Data
-------------------

All that remains now is to ingest the data. These steps can be followed at
:ref:`Greyscale Ingest Code Breakdown <break_down>`.
