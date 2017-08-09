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
of the state of Pennsylvania from 2011, and do a polygonal summary of an area
of interest to find the min and max classifications values of that area.

If you wish to follow along with this example, you will need to download the
NLCD data and the GeoJSON that represents the area of interest. Running these
two commands will download these files for you:

.. code:: console

   curl -o /tmp/NLCD2011_LC_Pennsylvannia.zip https://s3-us-west-2.amazonaws.com/prd-tnm/StagedProducts/NLCD/2011/landcover/states/NLCD2011_LC_Pennsylvania.zip?ORIG=513_SBDDG
   unzip /tmp/NLCD2011_LC_Pennsylvannia.zip
   curl -o /tmp/area_of_interest.geojson https://s3.amazonaws.com/geopyspark-test/area_of_interest.json

.. code:: python

  import json
  from functools import partial

  from geopyspark.geopycontext import GeoPyContext
  from geopyspark.geotrellis.constants import SPATIAL, ZOOM
  from geopyspark.geotrellis.geotiff_rdd import get
  from geopyspark.geotrellis.catalog import write

  from shapely.geometry import Polygon, shape
  from shapely.ops import transform
  import pyproj


  # Create the GeoPyContext
  geopysc = GeoPyContext(appName="example", master="local[*]")

  # Read in the NLCD tif that has been saved locally.
  # This tif represents the state of Pennsylvania.
  raster_rdd = get(geopysc=geopysc, rdd_type=SPATIAL,
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

  changelog <CHANGELOG>
  contributing

.. toctree::
  :maxdepth: 3
  :caption: Note Book Guides
  :glob:
  :hidden:

  demo-notebooks/core-concepts

.. toctree::
  :maxdepth: 4
  :caption: User Guides
  :glob:
  :hidden:

  guides/core_concepts
  guides/geopycontext
  guides/rdd
  guides/catalog

.. toctree::
  :maxdepth: 3
  :caption: Tutorials
  :glob:
  :hidden:

  tutorials/greyscale_ingest_example
  tutorials/greyscale_tile_server_example
  tutorials/sentinel_ingest_example
  tutorials/sentinel_tile_server_example

.. toctree::
  :maxdepth: 4
  :caption: Docs
  :glob:
  :hidden:

  docs/geopyspark
  docs/geopyspark.geotrellis
