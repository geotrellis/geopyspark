from geopyspark.keys import SpatialKey, SpaceTimeKey
from geopyspark.extent import Extent
from geopyspark.tile import TileArray

import numpy as np
import array


def tile_encoder(obj):
    (r, c) = obj.shape

    if obj.dtype.type == np.int8 or obj.dtype.type == np.uint8:
        values = array.array('B', obj.flatten()).tostring()
    else:
        values = obj.flatten().tolist()

    datum = {
            'cols': c,
            'rows': r,
            'cells': values,
            'noDataValue': obj.no_data_value
            }

    return datum

def extent_encoder(obj):
    datum = {
            'xmin': obj.xmin,
            'xmax': obj.xmax,
            'ymin': obj.ymin,
            'ymax': obj.ymax
            }

    return datum

def spatial_key_encoder(obj):
    datum = {
            'col': obj.col,
            'row': obj.row
            }

    return datum

def spacetime_key_encoder(obj):
    datum = {
            'col': obj.col,
            'row': obj.row,
            'instant': obj.instant
            }

    return datum

def multiband_encoder(obj):
    tile_datums = [tile_encoder(tile) for tile in obj]

    datum = {
            'bands': tile_datums
            }

    return datum

def tuple_encoder(obj):
    (a, b) = obj

    datum_1 = get_encoded_object(a)
    datum_2 = get_encoded_object(b)

    datum = {
            '_1': datum_1,
            '_2': datum_2
            }

    return datum

def key_value_record_encoder(obj):
    tuple_datums = [tuple_encoder(tup) for tup in obj]

    datum = {
            'pairs': tuple_datums
            }

    return datum

def get_encoded_object(obj, custom_class=None, custom_encoder=None):

    if isinstance(obj, custom_class):
        return custom_encoder(obj)

    elif isinstance(obj, list) and isinstance(obj[0], tuple):
        return key_value_record_encoder(obj)

    elif isinstance(obj, tuple):
        return tuple_encoder(obj)

    elif isinstance(obj, list):
        return multiband_encoder(obj)

    elif isinstance(obj, TileArray):
        return tile_encoder(obj)

    elif isinstance(obj, Extent):
        return extent_encoder(obj)

    elif isinstance(obj, SpatialKey):
        return spatial_key_encoder(obj)

    elif isinstance(obj, SpaceTimeKey):
        return spacetime_key_encoder(obj)

    else:
        raise Exception('Could not find encoder for', obj)
