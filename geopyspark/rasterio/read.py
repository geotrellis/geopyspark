import os
import math
import rasterio
import geopyspark as gps
import numpy as np


# On driver
if "GDAL_DATA" in os.environ:
    __GDAL_DATA = os.environ["GDAL_DATA"]
else:
    __GDAL_DATA = None


def __dataset_to_proj4(dataset):
    from osgeo import osr

    crs = dataset.get_crs()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(crs.wkt)
    proj4 = srs.ExportToProj4()
    return proj4


def __get_metadata(uri, dataset_to_proj4, xcols, ycols):

    # Potentially on worker
    if ("GDAL_DATA" not in os.environ) and (__GDAL_DATA != None):
        os.environ["GDAL_DATA"] = __GDAL_DATA

    def windows(ws, uri, proj4):
        for w in ws:
            ((row_start, row_stop), (col_start, col_stop)) = w

            left = bounds.left + (bounds.right - bounds.left)*(float(col_start)/width)
            right = bounds.left + (bounds.right - bounds.left)*(float(col_stop)/ width)
            bottom = bounds.top + (bounds.bottom - bounds.top)*(float(row_stop)/height)
            top = bounds.top + (bounds.bottom - bounds.top)*(float(row_start)/height)
            extent = gps.Extent(left, bottom, right, top)

            new_line = {}
            new_line['uri'] = uri
            new_line['window'] = w
            new_line['projected_extent'] = gps.ProjectedExtent(extent=extent, proj4=proj4)
            yield new_line

    try:
        with rasterio.open(uri) as dataset:
            bounds = dataset.bounds
            height = dataset.height
            width = dataset.width
            proj4 = dataset_to_proj4(dataset)
            tile_cols = (int)(math.ceil(width/xcols)) * xcols
            tile_rows = (int)(math.ceil(height/ycols)) * ycols
            ws = [((x, min(width-1, x + xcols)), (y, min(height-1, y + ycols))) for x in range(0, tile_cols, xcols) for y in range(0, tile_rows, ycols)]
            metadata = [i for i in windows(ws, uri, proj4)]
    except:
        metadata = []

    return metadata


def __get_data(metadatum):
    new_metadatum = metadatum.copy()

    with rasterio.open(metadatum['uri']) as dataset:
        new_metadatum['data'] = dataset.read(1, window=metadatum['window'])
        new_metadatum.pop('window')
        new_metadatum.pop('uri')

    return new_metadatum


def uri_to_pretiles(uri, dataset_to_proj4, xcols=512, ycols=512):
    metadata = __get_metadata(uri, dataset_to_proj4, xcols, ycols)
    return [__get_data(metadatum) for metadatum in metadata]


def pretile_to_tile(pretile, no_data_value=0):
    if isinstance(pretile, tuple):
        projected_extent = pretile[0]
        array = np.array([l['data'] for l in pretile[1]])
    elif isinstance(pretile, dict):
        projected_extent = pretile['projected_extent']
        array = np.array([pretile['data']])
    tile = gps.Tile.from_numpy_array(array, no_data_value=no_data_value)
    return (projected_extent, tile)
