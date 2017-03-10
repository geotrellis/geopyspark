from pyspark.serializers import Serializer, FramedSerializer

import io
import avro
import avro.io


class AvroSerializer(FramedSerializer):
    def __init__(self,
                 schema,
                 decoding_method=None,
                 encoding_method=None):

        self.schema_string = schema

        if decoding_method:
            self.decoding_method = decoding_method
        else:
            self.decoding_method = None

        if encoding_method:
            self.encoding_method = encoding_method
        else:
            self.encoding_method = None

    @property
    def schema(self):
        return avro.schema.Parse(self.schema_string)

    @property
    def schema_name(self):
        return self.schema().name

    @property
    def schema_dict(self):
        import json

        return json.loads(self.schema_string)

    @property
    def reader(self):
        return avro.io.DatumReader(self.schema)

    @property
    def datum_writer(self):
        return avro.io.DatumWriter(self.schema)

    """
    Serialize an object into a byte array.
    When batching is used, this will be called with an array of objects.
    """
    def dumps(self, obj):
        bytes_writer = io.BytesIO()

        encoder = avro.io.BinaryEncoder(bytes_writer)

        if self.encoding_method:
            datum = self.encoding_method(obj)
            self.datum_writer.write(datum, encoder)
        else:
            self.datum_writer.write(obj, encoder)

        return bytes_writer.getvalue()

    """
    Deserializes a byte array into a collection of python objects.
    """
    def loads(self, obj):
        buf = io.BytesIO(obj)

        decoder = avro.io.BinaryDecoder(buf)
        i = self.reader.read(decoder)

        if self.decoding_method:
            return [self.decoding_method(i)]
        else:
            return [i]
