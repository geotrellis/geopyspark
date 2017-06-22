RasterRDD and TiledRasterRDD
=============================

This section seeks to explain how to create and use ``RasterRDD`` and
``TiledRasterRDD``. Before continuing this example, it is suggested that
you read :ref:`data_rep`.


Creating RasterRDD and TiledRasterRDD
--------------------------------------

RasterRDD
~~~~~~~~~

Of the two different RDD classes, ``RasterRDD`` has the least number of ways
to be initialized. There are just two: (1) through reading GeoTiffs from the local
file system, S3, or HDFS; or (2) from an existing PySpark RDD.

From GeoTiffs
^^^^^^^^^^^^^^

The :meth:`~geopyspark.geotrellis.geotiff_rdd.get` method in
``geopyspark.geotrellis.geotiff_rdd`` creates an instance of ``RasterRDD`` from
GeoTiffs.

.. code:: python

   from geopyspark.geotrellis.constants import SPATIAL
   from geopyspark.geotrellis.geotiff_rdd import get

   from pyspark import SparkContext

   pysc = SparkContext(appName="rasterrdd-example", master="local")

   raster_rdd = get(pysc=pysc, rdd_type=SPATIAL, "path/to/your/geotiff.tif")

Note: If you have multiple GeoTiffs, you can just specify the directory where
they're all stored. Or if the GeoTiffs are spread out in multiple locations,
you can give ``get`` a ``list`` of the places to read in the GeoTiffs.


From PySpark RDDs
^^^^^^^^^^^^^^^^^^

The second option is to create a new ``RasterRDD`` from a PySpark RDD via the
:meth:`~geopyspark.geotrellis.rdd.RasterRDD.from_numpy_rdd` class method.
This step is a bit more involved than the last, as it requires the data within
the PySpark RDD to be formatted in a specific way.

.. code:: python

   from geopyspark.geotrellis import Extent
   from geopyspark.geotrellis.constants import SPATIAL
   from geopyspark.geotrellis.rdd import RasterRDD

   from pyspark import SparkContext

   import numpy as np

   pysc = SparkContext(appName="rasterrdd-example", master="local")

   arr = np.ones((1, 16, 16), dtype=int)

   # The raster data that will be contained in this RasterRDD will be 16x16,
   # and will have a noData value of -500.
   tile = {'no_data_value': -500, 'data': arr}

   extent = Extent(0.0, 1.0, 2.0, 3.0)

   # Since the RasterRDD will be SPATIAL, a ProjectedExtent is constructed.
   projected_extent = {'extent': extent, 'epsg': 3857}

   # Create a PySpark RDD that contains a single tuple, (projected_extent, tile)
   # Note: The order of the values in the tuple is important. ProjectedExtent
   # or TemporalProjectedExtent MUST Be the first element.
   rdd = pysc.parallelize([(projected_extent, tile)])

   raster_rdd = RasterRDD.from_numpy_rdd(pysc=pysc, rdd_type=SPATIAL, numpy_rdd=rdd)


TiledRasterRDD
~~~~~~~~~~~~~~~

Unlike ``RasterRDD``, ``TiledRasterRDD`` has multiple ways of being created.


From PySpark RDDs
^^^^^^^^^^^^^^^^^^

``TiledRasterRDD`` also has the class method,
:meth:`~geopyspark.geotrellis.rdd.TiledRasterRDD.from_numpy_rdd`.


.. code:: python

   from geopyspark.geotrellis import Extent, TileLayout, Bounds, LayoutDefinition
   from geopyspark.geotrellis.constants import SPATIAL
   from geopyspark.geotrellis.rdd import TiledRasterRDD

   from pyspark import SparkContext

   import numpy as np

   pysc = SparkContext(appName="tiledrasterrdd-example", master="local")

   data = np.array([[
       [1.0, 1.0, 1.0, 1.0, 1.0],
       [1.0, 1.0, 1.0, 1.0, 1.0],
       [1.0, 1.0, 1.0, 1.0, 1.0],
       [1.0, 1.0, 1.0, 1.0, 1.0],
       [1.0, 1.0, 1.0, 1.0, 0.0]]])

   # Data to be placed within the TiledRasterRDD.
   # Each value is a tuple where the first value is either a SpatialKey or a
   # SpaceTime. With the second being the tile.
   layer = [({'row': 0, 'col': 0}, {'no_data_value': -1.0, 'data': data}),
            ({'row': 1, 'col': 0}, {'no_data_value': -1.0, 'data': data}),
            ({'row': 0, 'col': 1}, {'no_data_value': -1.0, 'data': data}),
            ({'row': 1, 'col': 1}, {'no_data_value': -1.0, 'data': data})]

   # Creating the PySpark RDD.
   rdd = pysc.parallelize(layer)

   # All TiledRasterRDDs have metadata that describes the layout of data within
   # it. Therefore, in order to create it from a PySpark RDD, the metadata must
   # be either created, or taken from elsewhere.
   extent = Extent(0.0, 0.0, 33.0, 33.0)
   layout = TileLayout(2, 2, 5, 5)
   bounds = Bounds({'col': 0, 'row': 0}, {'col': 1, 'row': 1})
   layout_definition = LayoutDefinition(extent, layout)

   metadata = Metadata(
       bounds=bounds,
       crs='+proj=longlat +datum=WGS84 +no_defs ',
       cell_type='float32ud-1.0',
       extent=extent,
       layout_definition=layout_definition)

   tiled_rdd = TiledRasterRDD.from_numpy_rdd(pysc=pysc, rdd_type=SPATIAL,
                                             numpy_rdd=rdd, metadata=metadata)


Through Rasterization
^^^^^^^^^^^^^^^^^^^^^^

Another means of producing ``TiledRasterRDD`` is through rasterizing a Shapely
geometry via the :meth:`~geopyspark.geotrellis.rdd.TiledRasterRDD.rasterize`
method.

.. code:: python

   from geopyspark.geotrellis import Extent
   from geopyspark.geotrellis.constants import SPATIAL
   from geopyspark.geotrellis.rdd import TiledRasterRDD

   from pyspark import SparkContext

   from shapely.geometry import Polygon

   pysc = SparkContext(appName="tiledrasterrdd-example", master="local")

   extent = Extent(0.0, 0.0, 11.0, 11.0)

   polygon = Polygon([(0, 11), (11, 11), (11, 0), (0, 0)])

   # Creates a TiledRasterRDD from a Shapely Polygon. The resulting raster will
   # be 256x256 and all values within it are 1.
   tiled_rdd = TiledRasterRDD.rasterize(pysc=pysc, rdd_type=SPATIAL,
                                        geometry=polygon, extent=extent,
                                        cols=256, rows=256, fill_value=1)


Through Euclidean Distance
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The final way to create ``TiledRasterRDD`` is by calculating the Euclidean distance of
a Shapely geometry. :meth:`~geopyspark.geotrellis.rdd.TiledRasterRDd.euclidean_distance`
is the class method which does this. While you can use any geometry to perform
Euclidean distance, it is recommended **not** to use Polygons if they cover
many cells of the resulting raster. As this can impact performance in a
negative way.

.. code:: python

   from geopyspark.geotrellis import Extent
   from geopyspark.geotrellis.constants import SPATIAL
   from geopyspark.geotrellis.rdd import TiledRasterRDD

   from pyspark import SparkContext

   from shapely.geometry import MultiPoint
   import pyproj

   pysc = SparkContext(appName="tiledrasterrdd-example", master="local")

   # Shapely produces points in LatLng by default. However, GeoPySpark tends to
   # work with values in WebMercator, so we must reproject the geometries.
   latlong = pyproj.Proj(init='epsg:4326')
   webmerc = pyproj.Proj(init='epsg:3857')
   points = MultiPoint([pyproj.transform(latlong, webmerc, 1, 1),
                        pyproj.transform(latlong, webmerc, 2, 2)])

   # Makes a TiledRasterRDD from the Euclidean distance calculation.
   # The resulting TiledRasterRDD will have a zoom level of 7.
   tiled_rdd = TiledRasterRDD.euclidean_distance(pysc=pysc,
                                                 geometry=points,
                                                 source_crs=3857,
                                                 zoom=7)


Using RasterRDD and TiledRasterRDD
-----------------------------------

After initializing ``RasterRDD`` and/or ``TiledRasterRDD``, it is now time to
use them.


Common Methods
~~~~~~~~~~~~~~~

While different in terms of functionality, ``RasterRDD`` and ``TiledRasterRDD``
both share some methods.


Converting to a PySpark RDD
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you wish to you convert to a PySpark RDD, it can be done via the
``to_numpy_rdd`` method.

.. code:: python

   # RasterRDD
   raster_rdd.to_numpy_rdd()

   # TiledRasterRDD
   tiled_rdd.to_numpy_rdd()


Reclassifying Values
^^^^^^^^^^^^^^^^^^^^^

``reclassify`` can reclassify values in either ``RasterRDD`` or
``TiledRasterRDD``. This is done by binning each value in the RDD.

The ``boundary_strategy`` will determine how each value will be binned. These
are the strategies to choose from: ``GREATERTHAN``, ``GREATERTHANOREQUALTO``,
``LESSTHAN``, ``LESSTHANOREQUALTO``, and ``EXACT``.

If a value does not fall within the boundary, then it's given the
``no_data_value``. A different replacement can be used instead
with ``replace_nodata_with``.


.. code:: python

   from geopyspark.geotrellis.constants import EXACT, LESSTHAN

   value_map = {1: 0}
   # All values less than or equal to 1 will now become zero.
   # Any other number is now whatever the no_data_value is for this
   # TiledRasterRDD
   tiled_rdd.reclassify(value_map=value_map, data_type=int)

   value_map = {5.0: 10.0, 15.0: 20.0}

   # Only 5.0 and 15.0 will be reclassified. Everything else will become -1000.0
   tiled_rdd.reclassify(value_map=value_map, data_type=float, boundary_strategy=EXACT,
                        replace_no_data_with=-1000.0)


Min and Max
^^^^^^^^^^^^

``get_min_max`` will produce the min and max values of the RDD. They will always be
returned as ``float``\s. Regardless of the type of the input values.

.. code:: python

   tiled_rdd.get_min_max()


RasterRDD
~~~~~~~~~~

The purpose of ``RasterRDD`` is to store and format data to produce a
``TiledRasterRDD``. Thus, this class lacks the methods needed to perform any
kind of spatial analysis. It can be thought of as something of an "organizer".
Which sorts and lays out the data so that ``TiledRasterRDD`` can perform
operations on the data.


Collecting Metadata
^^^^^^^^^^^^^^^^^^^^

In order to convert a ``RasterRDD`` to a ``TiledRasterRDD`` the
:class:`~geopyspark.geotrellis.Metadata` must first be collected; as it
contains the information on how the data should be formatted and laid out in
the ``TiledRasterRDD``. :meth:`~geopyspark.geotrellis.rdd.RasterRDD.collect_metadata`
is used to obtain the metadata, and it can accept two different types of inputs
depending on how one wishes to layout the data.

The first option is to specify a :class:`~geopyspark.geotrellis.Extent` and an
:obj:`~geopyspark.geotrellis.TileLayout` for the ``Metadata``. Where the
``Extent`` is the area that will be covered by the ``Tile``\s and the
``TileLayout`` describes the ``Tile``\s and the grid they're arranged on.


.. code:: python

   from geopyspark.geotrellis import Extent, TileLayout

   extent = Extent(0.0, 0.0, 33.0, 33.0)
   tile_layout = TileLayout(2, 2, 256, 256)

   # The Metadata that will be returned will conform to the extent and tile
   # layout that was given. In this case, the rasters will be tiled into a 2x2
   # grid with each Tile having 256 cols and rows. This grid will cover the
   # area within the extent.
   md = raster_rdd.collect_metadata(extent=extent, layout=tile_layout)


The other option is to simply give ``collect_metadata`` the ``tile_size``
that each ``Tile`` should be in the resulting grid. ``Extent`` and
``TileLayout`` will be calculated from this size. Using this method will ensure
that the native resolutions of the rasters are kept.

.. code:: python

   # tile_size has a default value of 256. If this works for your case, then
   # you can just do this
   md = raster_rdd.collect_metadata()

   # Otherwise, you can specify your own tile_size.
   md = raster_rdd.collect_metadata(tile_size=512)


Formatting the Data to a Layout
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once ``Metadata`` has been obtained, ``RasterRDD`` will be able to format the
data, which will result in a new ``TiledRasterRDD`` instance. There are two
methods to do this: :meth:`~geopyspark.geotrellis.rdd.RasterRDD.cut_tiles` and
:meth:`~geopyspark.geotrellis.rdd.RasterRDD.tile_to_layout`.

Both of these methods have the same inputs and similar outputs, however, there is one key
difference between the two. ``cut_tiles`` will cut the rasters to the given
layout, but will not fix any overlap that may occur. Whereas ``tile_to_layout``
will cut and then merge together areas that are overlapped. This matters as
each ``Tile`` is referenced by a key, and if there's overlap than there could
be duplicate keys.

Therefore, it is recommended to use ``tile_to_layout`` to ensure there is no
duplication.

.. code:: python

   md = raster_rdd.collect_metadata()
   tiled_rdd = raster_rdd.tile_to_layout(layer_metadata=md)

   # resample_method can be set when doing the formatting. For this example,
   # BILINEAR will be used. The defatul method is NEARESTNEIGHBOR.

   from geopyspark.geotrellis.constants import BILINEAR

   tiled_rdd = raster_rdd.tile_to_layout(layer_metadata=md, resample_method=BILINEAR)


A Quicker Way to TiledRasterRDD
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`~geopyspark.geotrellis.rdd.RasterRDD.to_tiled_layer` allows the user to
layout their data and produce a ``TiledRasterRDD`` in just one step. This
method is ``collect_metadata`` and ``tile_to_layout`` combined, and is used to
save a little time when writing.

.. code:: python

   # Using Extent and TileLayout

   from geopyspark.geotrellis import Extent, TileLayout

   extent = Extent(0.0, 0.0, 33.0, 33.0)
   tile_layout = TileLayout(2, 2, 256, 256)

   tiled_rdd = raster_rdd.to_tiled_layer(extent=extent, layout=tile_layout)

   # Or using tile_size instead

   tiled_rdd = raster_rdd.to_tiled_layer()


TiledRasterRDD
~~~~~~~~~~~~~~~

``TiledRasterRDD`` will be the class that will see the most use. It provides
all the methods needed to perform a computations and analysis on the data. When
reading and saving layers, this class will be used.

A Note on Using Geometries
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before doing operations that involve geometries, it is important to check to
make sure that the geometry is in the correct projection. Geometries created
through Shapely are in LatLong. Unless the data in ``TiledRasterRDD`` is also
in this projection, the geometry being used will need to be reprojected.

.. code:: python

  from functools import partial

  from shapely.geometry import Polygon
  from shapely.ops import transform
  import pyproj

  polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])

  # Reporjects the geometry to WebMercator so that it will intersect with
  # the TiledRasterRDD.
  project = partial(
      pyproj.transform,
      pyproj.Proj(init='epsg:4326'),
      pyproj.Proj(init='epsg:3857'))

  reprojected_polygon = transform(project, geom)


.. _reproject_meth:

Reprojecting
^^^^^^^^^^^^^

Often the tiles within ``TiledRasterRDD`` will have to be reprojected. There is
a method to do this aptly named, :meth:`~geopyspark.geotrellis.rdd.TiledRasterRDD.reproject`.
If you wish to create a TMS server from this data, then this method should be
used to ensure that the layout will work when pyramiding (more on that in a
bit).

If you do not wish to create a TMS server, and just want to reproject the data,
then there are two different ways to different ways to do so.

.. code:: python

   # Using Extant and TileLayout

   from geopyspark.geotrellis import Extent, TileLayout

   extent = Extent(0.0, 0.0, 33.0, 33.0)
   tile_layout = TileLayout(2, 2, 256, 256)

   reprojected_rdd = tiled_rdd.reproject(target_crs=3857, extent=extent,
                                         layout=tile_layout)

   # Using tile_size

   reprojected_rdd = tiled_rdd.reproject(target_crs=3857)


If you want to make a TMS server, then there is only one option available
for reprojecting.

.. code:: python

   from geopyspark.geotrellis.constants import ZOOM

   reprojected_rdd = tiled_rdd.reproject(target_crs=3857, scheme=ZOOM)

   # Reprojecting with different tile_size

   reprojected_rdd = tiled_rdd.reproject(target_crs=3857, scheme=ZOOM, tile_size=512)

What is the difference between using and not using ``ZOOM``? It has to do with
how GeoTrellis represents the layout of the data in the RDD. There are three
different classes GeoTrellis uses: ``LayoutDefinition``,
``FloatingLayoutScheme`` and ``ZoomedLayoutScheme``. The exact nature and
differences between these classes will not be discussed here, rather, a brief
explanation will be given.

Because the resolution of images changes as one zooms in and out when using
a TMS server, the layout of the tiles changes. Neither ``LayoutDefinition`` or
``FloatingLayoutScheme`` have the ability to adjust the layout from a zoom.
Only ``ZoomedLayoutScheme`` can do this, which is why it must be set when
reprojecting.


Retiling
^^^^^^^^^

It is possible to change the layout of the tiles within ``TiledRasterRDD``
via :meth:`~geopyspark.geotrellis.rdd.TiledRasterRDD.tile_to_layout`.

.. code:: python

   from geopyspark.geotrellis import Extent, TileLayout, LayoutDefinition

   extent = Extent(100.0, 100.0, 250.0, 250.0)
   tile_layout = TileLayout(5, 5, 256, 256)
   layout_definition = TileDefinition(extent, tile_layout)

   retiled_rdd = tiled_rdd.tile_to_layout(layout=layout_definition)


Masking
^^^^^^^

By using :meth:`~geopyspark.geotrellis.rdd.TiledRasterRDD.mask`, the
``TiledRasterRDD`` can be masekd using one or more Shapely geometries.

.. code:: python

   from shapely.geometry import Polygon

  polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])

  # The resulting TiledRasterRDD will only contain values that were interested
  # by this Polygon

  masked_rdd = tiled_rdd.mask(geometries=polygon)


Stitching
^^^^^^^^^^

Using :meth:`~geopyspark.geotrellis.rdd.TiledRasterRDD.stitch` will produce
a single raster by stitching together all of the tiles within the
``TiledRasterRDD``. This can only be done with ``SPATIAL`` RDDs, and is not
recommended if the data contained within is large. As it can cause crashes due
to its size.

.. code:: python

   raster = tiled_rdd.stitch()


Pyramiding
^^^^^^^^^^^

Before creating a TMS server, a ``TiledRasterRDD`` needs to be pyramided first.
:meth:`~geopyspark.geotrellis.rdd.TiledRasterRDD.pyramid` will create a new
``TiledRasterRDD`` for each zoom level, and the resulting list can then be
either be accessed to fetch specific tiles or can be saved for later use.

.. code:: python

   # Creates 12 new TiledRasterRDDs where each one has a different layout
   # depending on its zoom level.
   pyramided_rdds = tiled_rdd.pyramid(start_zoom=12, end_zoom=1)

Why is ``start_zoom`` greater than ``end_zoom``? This is because ``start_zoom``
represents the lowest or most zoomed level of the pyramid. And the pyramiding
process starts with the greatest zoom and works its way up to the most zoomed
out.


Operations
^^^^^^^^^^^

``TiledRasterRDD``\s can perform both local and focal operations.

Local
*****

Performing local operations with ``TiledRasterRDD``\s can be performed with
``int``\s, ``float``\s, or other ``TiledRasterRDD``\s.

.. code:: python

   # All values will have one added to them
   tiled_rdd + 1

   # Find the average of two TiledRasterRDDs
   (tiled_rdd_1 + tiled_rdd_2) / 2

   # The position of TiledRasterRDD in the operation doesn't matter, so it can
   # be used on either side of of the operation.
   1 / (5 - tiled_rdd)


Focal
*****

Focal operations are done by selecting both a ``neighborhood`` and a
``operation``. Because the inputs must be sent over to Scala, the ``operation``
must be entered in the form of a constant.

The values used to represent ``operation`` are: ``SUM``, ``MIN``, ``MAX``,
``MEAN``, ``MEDIAN``, ``MODE``, ``STANDARDDEVIATION``, ``ASPECT``, and
``SLOPE``. These are all of the current available focal operations that can be
done in GeoPySpark.

``neighborhood`` can be specified with either a
:class:`~geopyspark.geotrellis.neighborhoods.Neighboorhod` sub-class, or a
constant.

.. code:: python

   from geopyspark.geotrellis.neighborhoods import Square
   from geopyspakr.geotrellis.constants import SLOPE

   # Creates a Square neighborhood. Setting extent to 1 will mean that only one
   # cell past the focus of the bounding box will be included in the
   # neighborhood. Thus it creates a neighborhood that is 3x3 cells in size.
   square_neighborhood = Square(extent=1)

   # Calculate the slope for each neighborhood in the TiledRasterRDD
   slope_rdd = tiled_rdd.focal(operation=SLOPE, neighborhood=square_neighborhood)


   # To perform a focal operation with creating a Neighborhood class.

   from geopyspark.geotrellis.constants import SQUARE

   # Since a class wasn't initialized, the parameters to make the neighborhood
   # must be passed in to the method. Square only requires one parameter, so
   # only param_1 needs to be set.
   slope_rdd = tiled_rdd.focal(operation=SLOPE, neighborhood=SQUARE, param_1=1)


Polygonal Summary Methods
^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to local and focal methods, ``TiledRasterRDD`` can also perform
polygonal summary methods. Using Shapely geometries, one can find the min, max,
sum, and mean of all of the values intersected by the geometry.

.. code:: python

   from shapely.geometry import Polygon

   polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])

   # Finds the min value that falls inside the Polygon. The data type of the
   # values within the Tiles must be stated. For this example, they are ints.
   tiled_rdd.polygonal_min(geometry=polygon, data_type=int)

   # Finds the max value that falls inside the Polygon.
   tiled_rdd.polygonal_max(geometry=polygon, data_type=float)

   # Finds the sum of the values that fall inside the Polygon.
   tiled_rdd.polygonal_sum(geometry=polygon, data_type=int)

   # polygonal_mean will always return a float, so there's no need to set
   # data_type.
   tiled_rdd.polygonal_mean(geometry=polygon)


Cost Distance
^^^^^^^^^^^^^^

It's possible to calculate the cost distance of a ``TiledRasterRDD`` via
:meth:`~geopyspark.geotrellis.rdd.TiledRasterRDD.cost_distance`.

.. code:: python

   from shapely.geometry import Point

   points = [Point(0, 0), Point(1, 2)]

   tiled_rdd.cost_distance(geometries=points, max_distance=144000)
