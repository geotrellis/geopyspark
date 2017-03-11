import array
import numpy as np


class AvroRegistry(object):
    # DECODERS

    @staticmethod
    def tile_decoder(schema_dict):
        cells = schema_dict['cells']

        if isinstance(cells, bytes):
            cells = bytearray(cells)

        # cols and rows are opposte for GeoTrellis ArrayTiles and Numpy Arrays
        arr = np.array(cells).reshape(schema_dict['rows'], schema_dict['cols'])

        if 'noDataValue' in schema_dict:
            tile_dict = {'data': arr, 'no_data_value': schema_dict['noDataValue']}
        else:
            tile_dict = {'data': arr}

        return tile_dict

    @classmethod
    def multiband_decoder(cls, schema_dict):
        bands = schema_dict['bands']
        tile_dicts = [cls.tile_decoder(band) for band in bands]

        tiles = [tile['data'] for tile in tile_dicts]
        no_data = tile_dicts[0]['no_data_value']

        return {'data': np.array(tiles), 'no_data_value': no_data}

    @staticmethod
    def tuple_decoder(schema_dict, key_decoder=None, value_decoder=None):
        schema_1 = schema_dict['_1']
        schema_2 = schema_dict['_2']

        if key_decoder and value_decoder:
            return (key_decoder(schema_1), value_decoder(schema_2))
        elif key_decoder:
            return (key_decoder(schema_1), schema_2)
        elif value_decoder:
            return (schema_1, value_decoder(schema_2))
        else:
            return (schema_1, schema_2)

    # ENCODERS

    @staticmethod
    def tile_encoder(obj):
        arr = obj['data']

        if len(arr.shape) > 2:
            (rows, cols) = (arr.shape[1], arr.shape[2])
        else:
            (rows, cols) = arr.shape

        if arr.dtype.name == 'int8' or arr.dtype.name == 'uint8':
            values = array.array('B', arr.flatten()).tostring()
        else:
            values = arr.flatten().tolist()

        if 'no_data_value' in obj:
            datum = {
                'cols': cols,
                'rows': rows,
                'cells': values,
                'noDataValue': obj['no_data_value']
            }

        else:
            datum = {
                'cols': cols,
                'rows': rows,
                'cells': values
            }

        return datum

    @classmethod
    def multiband_encoder(cls, obj):

        def create_dict(index):
            return {'data': obj['data'][index, :, :], 'no_data_value': obj['no_data_value']}

        bands = obj['data'].shape[0]
        tile_datums = [cls.tile_encoder(create_dict(x)) for x in range(bands)]

        datum = {
            'bands': tile_datums
        }

        return datum

    @staticmethod
    def tuple_encoder(obj, key_encoder=None, value_encoder=None):
        (value_1, value_2) = obj

        if key_encoder and value_encoder:
            datum_1 = key_encoder(value_1)
            datum_2 = value_encoder(value_2)
        elif key_encoder:
            datum_1 = key_encoder(value_1)
            datum_2 = value_2
        elif value_encoder:
            datum_1 = value_1
            datum_2 = value_encoder(value_2)
        else:
            datum_1 = value_1
            datum_2 = value_2

        return {'_1': datum_1, '_2': datum_2}
