from PIL import Image
import numpy as np
import io

from py4j.clientserver import ClientServer, JavaParameters, PythonParameters
from geopyspark.geotrellis.rdd import Pyramid

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
        # render_function: numpyarry => Image
        self.render_function = render_function

    def render(self, cells, cols, rows): # return `bytes`
        """A function to convert an array to an image.

        Args:
            cells (bytes): A linear array of bytes representing the contents of
                a tile
            rows (int): The number of rows in the final array
            cols (int): The number of cols in the final array

        Returns:
            [bytes] representing an image
        """
        try:
            # tile = np.array(list(cells)) # turn tile to array with bands
            print("Reshaping to {}x{} matrix".format(rows, cols))
            tile = np.reshape(np.frombuffer(cells, dtype="uint8"), (1, rows, cols)) # turn tile to array with bands
            print("Rendering tile")
            image=self.render_function(tile)
            print("Saving result")
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
        self.pysc._gateway.start_callback_server()

    def set_handshake(self, handshake):
        self.server.set_handshake(handshake)
        self.handshake = handshake

def s3_catalog_tms_server(pysc, bucket, root, catalog, colormap):
    """A function to create a TMS server for a catalog stored in an S3 bucket.

    Args:
        bucket (string): The name of the S3 bucket
        root (string): The key in the bucket containing the catalog
        catalog (string): The name of the catalog
        colormap (ColorMap): A ColorMap to use in rendering the catalog tiles

    Returns:
        [TMSServer]
    """
    server = pysc._gateway.jvm.geopyspark.geotrellis.tms.TMSServer.serveS3Catalog(bucket, root, catalog, colormap.cmap)
    return TMSServer(pysc, server)

def remote_tms_server(pysc, pattern_url):
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
    return TMSServer(pysc, server)


def rdd_tms_server(pysc, pyramid, colormap):
    if isinstance(pyramid, list):
        pyramid = Pyramid(pyramid)
    rdd_levels = {k: v.srdd.rdd() for k, v in pyramid.levels.items()}
    server = pysc._gateway.jvm.geopyspark.geotrellis.tms.TMSServer.serveSpatialRdd(rdd_levels, colormap.cmap, 0)
    return TMSServer(pysc, server)
