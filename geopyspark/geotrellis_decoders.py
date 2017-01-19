from geopyspark.serialization_constants import *


def tile_decoder(i):
    from geopyspark.tile import TileArray
    import numpy as np

    cells = i['cells']

    if isinstance(cells, bytes):
        cells = bytearray(cells)

    # cols and rows are opposte for GeoTrellis ArrayTiles and Numpy Arrays
    arr = np.array(cells).reshape(i['rows'], i['cols'])
    tile = TileArray(arr, i['noDataValue'])

    return tile

def extent_decoder(i):
    from geopyspark.extent import Extent

    return Extent(i['xmin'], i['ymin'], i['xmax'], i['ymax'])

def spatial_key_decoder(i):
    from geopyspark.keys import SpatialKey

    return SpatialKey(i['col'], i['row'])

def spacetime_key_decoder(i):
    from geopyspark.keys import SpaceTimeKey

    return SpaceTimeKey(i['col'], i['row'], i['instant'])

def multiband_decoder(i):
    bands = i['bands']
    objs = [tile_decoder(x) for x in bands]

    return objs

def tuple_decoder(i, schema_dict):

    schema_1 = i['_1']
    schema_2 = i['_2']

    (a, b) = schema_dict['fields']

    name_1 = a['type']['name']
    if isinstance(b['type'], list):
        # The 'name' parameter does not effect the handling of
        # tiles in _make_object, so any name will do.  If type is
        # an array but this is not a tile, then undefined
        # behavior.
        if b['type'][0]['name'] in TILES:
            name_2 = b['type'][0]['name']
        else:
            name_2 = None
    else:
        name_2 = b['type']['name']

    decoder_1 = get_decoder(name=name_1)
    decoder_2 = get_decoder(name=name_2)

    result = (decoder_1(schema_1), decoder_2(schema_2))

    return result

def key_value_record_decoder(i, schema_dict):
    tuple2 = schema_dict['fields'][0]['type']['items']
    pairs = i['pairs']

    objs = [tuple_decoder(x, schema_dict=tuple2) for x in pairs]

    return objs

def get_decoder(name, custom_name=None, custom_decoder=None):

    if name == custom_name:
        return custom_decoder

    elif name == KEYVALUERECORD:
        return key_value_record_decoder

    elif name == TUPLE:
        return tuple_decoder

    elif name == ARRAYMULTIBANDTILE:
        return multiband_decoder

    elif name in TILES:
        return tile_decoder

    elif name == EXTENT:
        return extent_decoder

    elif name == SPATIALKEY:
        return spatial_key_decoder

    elif name == SPACETIMEKEY:
        return spacetime_key_decoder

    else:
        raise Exception("Could not find a decoder for", name)
