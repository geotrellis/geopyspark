import io
import numpy as np

from geopyspark.geotrellis.color import ColorMap
from geopyspark.geotrellis.layer import Pyramid
from geopyspark.geotrellis.protobufcodecs import multibandtile_decoder

class TileRender(object):
    """A Python implementation of the Scala geopyspark.geotrellis.tms.TileRender
    interface.  Permits a callback from Scala to Python to allow for custom
    rendering functions.
    """

    def __init__(self, render_function):
        """Default constructor.

        Args:
            render_function (numpy array => bytes): A function to convert a numpy
                array to a collection of bytes giving a binary image file.

        Returns:
            [TileRender]
        """
        print("Created Python TileRender object")
        # render_function: numpyarry => Image
        self.render_function = render_function

    def requiresEncoding(self):
        return True

    def renderEncoded(self, scala_array): # return `bytes`
        """A function to convert an array to an image.

        Args:
            cells (bytes): A linear array of bytes representing the contents of
                a tile
            rows (int): The number of rows in the final array
            cols (int): The number of cols in the final array

        Returns:
            [bytes] representing an image
        """
        # self.sc._gateway.jvm.System.out.println("Python renderer called!")
        try:
            tile = multibandtile_decoder(scala_array)
            # self.sc._gateway.jvm.System.out.println("Received tile of type {}".format(str(type(tile))))
            cells = tile.cells
            bands, rows, cols = cells.shape
            # self.sc._gateway.jvm.System.out.println("Rendering {}x{} tile ({} bands)".format(rows, cols, bands))
            image = self.render_function(cells)
            # self.sc._gateway.jvm.System.out.println("Saving result")
            bio = io.BytesIO()
            image.save(bio, 'PNG')
            return bio.getvalue()
        except Exception:
            from traceback import print_exc
            print_exc()

    class Java:
        implements = ["geopyspark.geotrellis.tms.TileRender"]

class TMSServer(object):
    def __init__(self, pysc, server):
        self.pysc = pysc
        self.server = server
        self.handshake = ''
        pysc._gateway.start_callback_server()

    def set_handshake(self, handshake):
        self.server.set_handshake(handshake)
        self.handshake = handshake

    @classmethod
    def s3_catalog_tms_server(cls, pysc, bucket, root, catalog, display):
        """A function to create a TMS server for a catalog stored in an S3 bucket.

        Args:
            bucket (string): The name of the S3 bucket
            root (string): The key in the bucket containing the catalog
            catalog (string): The name of the catalog
            display (ColorMap, TileRender): A ColorMap to use in rendering the catalog tiles

        Returns:
            [TMSServer]
        """
        if isinstance(display, ColorMap):
            server = pysc._gateway.jvm.geopyspark.geotrellis.tms.TMSServer.serveS3Catalog(bucket, root, catalog, display.cmap)
        elif isinstance(display, TileRender):
            server = pysc._gateway.jvm.geopyspark.geotrellis.tms.TMSServer.serveS3CatalogCustom(bucket, root, catalog, display)
        else:
            raise ValueError("Must specify the display parameter as a ColorMap or TileRender object")

        return cls(pysc, server)

    @classmethod
    def remote_tms_server(cls, pysc, pattern_url):
        """A function to create a TMS server delivering tiles from a remote TMS server

        Args:
            pattern_url (string): A string giving the form of the URL where tiles
                are stored.  The pattern should contain the literals '{z}', '{x}',
                and '{y}' giving the zoom, x, and y keys of the desired tile,
                respectively.

        Returns:
            [TMSServer]
        """

        server = pysc._gateway.jvm.geopyspark.geotrellis.tms.TMSServer.serveRemoteTMSLayer(pattern_url)
        return cls(pysc, server)

    @classmethod
    def rdd_tms_server(cls, pysc, pyramid, display):
        """Creates a TMS server for displaying a Pyramided RDD.

        Args:
            pysc (SparkContext): The current SparkContext
            pyramid (Pyramid): The pyramided RDD
            display (ColorMap, TileRender): A color map or TileRender object
                that will be used for display.

        Returns:
            [TMSServer]
        """
        if isinstance(pyramid, list):
            pyramid = Pyramid(pyramid)
        rdd_levels = {k: v.srdd.rdd() for k, v in pyramid.levels.items()}

        if isinstance(display, ColorMap):
            server = pysc._gateway.jvm.geopyspark.geotrellis.tms.TMSServer.serveSpatialRdd(rdd_levels, display.cmap, 0)
        elif isinstance(display, TileRender):
            server = pysc._gateway.jvm.geopyspark.geotrellis.tms.TMSServer.serveSpatialRddCustom(rdd_levels, display, 0)
        else:
            raise ValueError("Must specify the display parameter as a ColorMap or TileRender object")

        return cls(pysc, server)
