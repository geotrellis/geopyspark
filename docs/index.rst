What is GeoPySpark?
--------------------

*GeoPySpark* is a Python language binding library of the Scala library,
`GeoTrellis <https://github.com/locationtech/geotrellis>`_. Like GeoTrellis,
this project is released under the Apache 2 License.

GeoPySpark seeks to utilize GeoTrellis to allow for the reading, writing, and
operating on raster data. Thus, its able to scale to the data and still be able
to perform well.

In addition to raster processing, GeoPySpark allows for rasters to be rendered
into PNGs. One of the goals of this project to be able to process rasters at
web speeds and to perform batch processing of large data sets.

Why GeoPySpark?
----------------

Raster processing in Python has come a long way; however, issues still arise
as the size of the dataset increases. Whether it is performance or ease of use,
these sorts of problems will become more common as larger amounts of data are
made available to the public.

One could turn to GeoTrellis to resolve the aforementioned problems (and one
should try it out!), yet this brings about new challenges. Scala, while a
powerful language, has something of a steep learning curve. This can put off
those who do not have the time and/or interest in learning a new language.

By having the speed and scalability of Scala and the ease of Python,
GeoPySpark is then the remedy to this predicament.

A Quick Example
----------------

Here is a quick example of GeoPySpark. In the following code, we take NLCD data
of the state of Pennsylvania from 2011, and do a masking operation on it with
a Polygon that represents an area of interest. This masked layer is then saved.

If you wish to follow along with this example, you will need to download the
NLCD data and unzip it.. Running these two commands will complete these tasks
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
--------------------

If you need help, have questions, or would like to talk to the developers (let us
know what you're working on!) you can contact us at:

 * `Gitter <https://gitter.im/geotrellis/geotrellis>`_
 * `Mailing list <https://locationtech.org/mailman/listinfo/geotrellis-user>`_

As you may have noticed from the above links, those are links to the GeoTrellis
Gitter channel and mailing list. This is because this project is currently an
offshoot of GeoTrellis, and we will be using their mailing list and gitter
channel as a means of contact. However, we will form our own if there is
a need for it.


.. toctree::
  :maxdepth: 2
  :caption: Home
  :hidden:

  Changelog <CHANGELOG>
  contributing

.. toctree::
  :maxdepth: 5
  :caption: User Guides
  :hidden:

  guides/core-concepts
  guides/layers
  guides/catalog
  guides/map-algebra
  guides/visualization
  guides/tms

.. toctree::
  :maxdepth: 2
  :caption: Tutorials
  :glob:
  :hidden:

  tutorials/ingesting-an-image
  tutorials/reading-in-sentinel-data

.. toctree::
  :maxdepth: 2
  :caption: API Reference
  :glob:
  :hidden:

  docs/geopyspark
  docs/geopyspark.geotrellis
  docs/geopyspark.vector_pipe
