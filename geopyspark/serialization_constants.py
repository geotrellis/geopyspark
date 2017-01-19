"""
These constants are the various names of avro schema files and are used to
serialize/deserialize the avro schemas that come back-and-forth between
python and scala
"""

EXTENT = 'Extent'

TILES = ['BitArrayTile', 'ByteArrayTile', 'UByteArrayTile', 'ShortArrayTile',
        'UShortArrayTile', 'IntArrayTile', 'FloatArrayTile', 'DoubleArrayTile']

ARRAYMULTIBANDTILE = 'ArrayMultibandTile'

SPATIALKEY = 'SpatialKey'

SPACETIMEKEY = 'SpaceTimeKey'

TUPLE = 'Tuple2'

KEYVALUERECORD = 'KeyValueRecord'

COLLECTIONS = [TUPLE, KEYVALUERECORD]
