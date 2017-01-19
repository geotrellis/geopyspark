from pyspark.serializers import Serializer, FramedSerializer
from geopyspark.geotrellis_decoders import get_decoder
from geopyspark.geotrellis_encoders import get_encoded_object
from geopyspark.serialization_constants import COLLECTIONS

import io
import avro
import avro.io


class AvroSerializer(FramedSerializer):

    def __init__(self,
            schema_json,
            custom_name=None,
            custom_decoder=None,
            custom_class=None,
            custom_encoder=None):

        self._schema_json = schema_json

        self.custom_name = custom_name
        self.custom_decoder = custom_decoder

        self.custom_class = custom_class
        self.custom_encoder = custom_encoder

    def schema(self):
        return avro.schema.Parse(self._schema_json)

    def schema_name(self):
        return self.schema().name

    def schema_dict(self):
        import json

        return json.loads(self._schema_json)

    def reader(self):
        return avro.io.DatumReader(self.schema())

    def datum_writer(self):
        return avro.io.DatumWriter(self.schema())

    """
    Serialize an object into a byte array.
    When batching is used, this will be called with an array of objects.
    """
    def dumps(self, obj, schema):
        s = avro.schema.Parse(schema)

        writer = avro.io.DatumWriter(s)
        bytes_writer = io.BytesIO()

        encoder = avro.io.BinaryEncoder(bytes_writer)
        datum = get_encoded_object(obj,
                custom_class=self.custom_class,
                custom_encoder=self.custom_encoder)
        writer.write(datum, encoder)

        return bytes_writer.getvalue()

    """
    Deserializes a byte array into a collection of python objects.
    """
    def loads(self, obj):
        buf = io.BytesIO(obj)
        decoder = avro.io.BinaryDecoder(buf)
        i = self.reader().read(decoder)

        decoder = get_decoder(name=self.schema_name(),
                custom_name=self.custom_name,
                custom_decoder=self.custom_decoder)

        if self.schema_name() in COLLECTIONS:
            result = decoder(i, self.schema_dict())
        else:
            result = decoder(i)

        return [result]
