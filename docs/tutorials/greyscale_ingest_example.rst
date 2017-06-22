.. _greyscale_ingest_example:

Ingesting a Grayscale Image
****************************

This example shows how to ingest a grayscale image and save the results
locally.

The Code
========

Here's the code to run the ingest.

.. code:: python

  from geopyspark.geotrellis.constants import SPATIAL, ZOOM
  from geopyspark.geotrellis.catalog import write
  from geopyspark.geotrellis.geotiff_rdd import get

  from pyspark import SparkContext


  pysc = SparkContext(appName="python-ingest", master="local[*]")

  # Read the GeoTiff from S3
  rdd = get(pysc, SPATIAL, "file:///tmp/cropped.tif")

  metadata = rdd.collect_metadata()

  # tile the rdd to the layout defined in the metadata
  laid_out = rdd.tile_to_layout(metadata)

  # reproject the tiled rasters using a ZoomedLayoutScheme
  reprojected = laid_out.reproject("EPSG:3857", scheme=ZOOM)

  # pyramid the TiledRasterRDD to create 12 new TiledRasterRDDs
  # one for each zoom level
  pyramided = reprojected.pyramid(start_zoom=12, end_zoom=1)

  # Save each TiledRasterRDD locally
  for tiled in pyramided:
      write("file:///tmp/python-catalog", "python-ingest", tiled)


Running the Code
-----------------

Before you can run this example, the example file will have to be downloaded.
Run this command to save the file locally in the ``/tmp`` directory.

.. code:: console

   curl -o /tmp/cropped.tif https://s3.amazonaws.com/geopyspark-test/example-files/cropped.tif

Running the code is simple, and you have two different ways of doing it.

The first is to copy and paste the code into a console like, iPython, and then
running it.

The second is to place this code in a Python file and then saving it. To run it
from the file, go to the directory the file is in and run this command

.. code:: console

  python3 file.py

Just replace ``file.py`` with whatever name you decided to call the file.

.. _break_down:

Breaking Down the Code
=======================

Now that the code has been written let's go through it step-by-step to see
what's actually going on.

Reading in the Data
--------------------

.. code:: python

 pysc = SparkContext(appName="python-ingest", master="local[*]")

 # Read the GeoTiff from S3
 rdd = get(pysc, SPATIAL, "file:///tmp/cropped.tif")

Before doing anything when using GeoPySpark, it's best to create a
``SparkContext`` instance.

After the creation of ``pysc`` we can now read the data. For this example,
we will be reading a single GeoTiff that contains only spatial data
(hence :const:`~geopyspark.geotrellis.SPATIAL`). This will create an instance
of :class:`~geopyspark.geotrellis.rdd.RasterRDD` which will allow us to start
working with our data.


Collecting the Metadata
------------------------

.. code:: python

 metadata = rdd.collect_metadata()

Before we can begin formatting the data to our desired layout, we must first
collect the :class:`~geopyspark.geotrellis.Metadata` of the entire RDD. The metadata itself will contain
the :obj:`~geopyspark.geotrellis.TileLayout` that the data will be formatted to. There are various
ways to collect the metadata depending on how you want the layout to look
(see :meth:`~geopyspark.geotrellis.rdd.RasterRDD.collect_metadata`), but for
this example, we will just go with the default parameters.


Tiling the Data
----------------

.. code:: python

 # tile the rdd to the layout defined in the metadata
 laid_out = rdd.tile_to_layout(metadata)

 # reproject the tiled rasters using a ZoomedLayoutScheme
 reprojected = laid_out.reproject("EPSG:3857", scheme=ZOOM)

With the metadata collected, it is now time to format the data within the
RDD to our desired layout. The aptly named, :meth:`~geopyspark.geotrellis.rdd.RasterRDD.tile_to_layout`,
method will cut and arrange the rasters in the RDD to the layout within the
metadata; giving us a new class instance of :class:`~geopyspark.geotrellis.rdd.TiledRasterRDD`.

Having this new class will allow us to perform the final steps of our ingest.
While the tiles are now in the correct layout, their CRS is not what we want.
It would be great if we could make a tile server from our ingested data, but to
do that we'll have to change the projection.
:meth:`~geopysaprk.geotrellis.rdd.TiledRasterRDD.reproject` will be able to
help with this. **If you wish to pyramid your data, it must have a ``scheme``
of ``ZOOM`` before the pyramiding takes place**. Read more about why
:ref:`here <reproject_meth>`.


Pyramiding the Data
--------------------

.. code-block:: python

 # pyramid the TiledRasterRDD to create 12 new TiledRasterRDDs
 # one for each zoom level
 pyramided = reprojected.pyramid(start_zoom=12, end_zoom=1)

Now it's time to pyramid! Using our reprojected data, we can create 12 new
instances of ``TiledRasterRDD``. Each instance represents the data within the
RDD at a specific zoom level. **Note**: The ``start_zoom`` is always the larger
number when pyramiding.


Saving the Ingest Locally
--------------------------

.. code-block:: python

 # Save each TiledRasterRDD locally
 for tiled in pyramided:
     write("file:///tmp/python-catalog", "python-ingest", tiled)

All that's left to do now is to save it. Since ``pyramided`` is just a list of
``TiledRasterRDD``, we can just loop through it and save each element one at a
time.
