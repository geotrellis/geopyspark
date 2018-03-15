"""This module contains the ``Histogram`` class which is a wrapper of the GeoTrellis Histogram
class.
"""

import json
from geopyspark import get_spark_context

__all__ = ['Histogram']


class Histogram(object):
    """A wrapper class for a GeoTrellis Histogram.

    The underlying histogram is produced from the values within a
    :class:`~geopyspark.geotrellis.layer.TiledRasterLayer`. These values represented by the
    histogram can either be ``Int`` or ``Float`` depending on the data type of the cells in the
    layer.

    Args:
        scala_histogram (py4j.JavaObject): An instance of the GeoTrellis histogram.

    Attributes:
        scala_histogram (py4j.JavaObject): An instance of the GeoTrellis histogram.
    """

    def __init__(self, scala_histogram):
        self.scala_histogram = scala_histogram

    @classmethod
    def from_dict(cls, value):
        """Encodes histogram from a ``dict``.

        Returns:
            :class:`~geopyspark.geotrellis.histogram.Histogram`
        """

        pysc = get_spark_context()
        histogram_json = json.dumps(value)
        scala_histogram = pysc._gateway.jvm.geopyspark.geotrellis.Json.readHistogram(histogram_json)

        return cls(scala_histogram)

    def to_dict(self):
        """Converts this ``Histogram`` instance into a ``dict``.

        Returns:
            dict
        """

        pysc = get_spark_context()
        histogram_json = pysc._gateway.jvm.geopyspark.geotrellis.Json.writeHistogram(self.scala_histogram)

        return json.loads(histogram_json)

    def min(self):
        """The smallest value of the histogram.

        This will return either an ``int`` or ``float`` depedning on the type of values
        within the histogram.

        Returns:
            int or float
        """

        return self.scala_histogram.minValue().get()

    def max(self):
        """The largest value of the histogram.

        This will return either an ``int`` or ``float`` depedning on the type of values
        within the histogram.

        Returns:
            int or float
        """

        return self.scala_histogram.maxValue().get()

    def min_max(self):
        """The largest and smallest values of the histogram.

        This will return either an ``int`` or ``float`` depedning on the type of values
        within the histogram.

        Returns:
            (int, int) or (float, float)
        """

        tup = self.scala_histogram.minMaxValues().get()

        return (tup._1(), tup._2())

    def mean(self):
        """Determines the mean of the histogram.

        Returns:
            float
        """

        return self.scala_histogram.mean().get()

    def mode(self):
        """Determines the mode of the histogram.

        This will return either an ``int`` or ``float`` depedning on the type of values
        within the histogram.

        Returns:
            int or float
        """

        return self.scala_histogram.mode().get()

    def median(self):
        """Determines the median of the histogram.

        Returns:
            float
        """

        return self.scala_histogram.mean().get()

    def values(self):
        """Lists each indiviual value within the histogram.

        This will return a list of either ``int``s or ``float``s depedning on the type of values
        within the histogram.

        Returns:
            [int] or [float]
        """

        return list(self.scala_histogram.values())

    def item_count(self, item):
        """Returns the total number of times a given item appears in the histogram.

        Args:
            item (int or float): The value whose occurences should be counted.

        Returns:
            int: The total count of the occurences of ``item`` in the histogram.
        """

        return self.scala_histogram.itemCount(item)

    def cdf(self):
        """Returns the cdf of the distribution of the histogram.

        Returns:
            [(float, float)]
        """

        cdfs = list(self.scala_histogram.cdf())

        return [(cdf._1(), cdf._2()) for cdf in cdfs]

    def bucket_count(self):
        """Returns the number of buckets within the histogram.

        Returns:
            int
        """

        return self.scala_histogram.bucketCount()

    def bin_counts(self):
        """Returns a list of tuples where the key is the bin label value and the
        value is the label's respective count.

        Returns:
            [(int, int)] or [(float, int)]
        """

        labels = self.values()
        counts = list(map(self.item_count, labels))

        return list(zip(labels, counts))

    def quantile_breaks(self, num_breaks):
        """Returns quantile breaks for this Layer.

        Args:
            num_breaks (int): The number of breaks to return.

        Returns:
            [int]
        """

        return list(self.scala_histogram.quantileBreaks(num_breaks))

    def merge(self, other_histogram):
        """Merges this instance of ``Histogram`` with another. The resulting ``Histogram``
        will contain values from both ``Histogram``s

        Args:
            other_histogram (:class:`~geopyspark.geotrellis.histogram.Histogram`): The
                ``Histogram`` that should be merged with this instance.

        Returns:
            :class:`~geopyspark.geotrellis.histogram.Histogram`
        """

        return Histogram(self.scala_histogram.merge(other_histogram.scala_histogram))

    def to_dict(self):
        """Encodes histogram as a dictionary

        Returns:
           ``dict``
        """

        pysc = get_spark_context()
        histogram_json = pysc._gateway.jvm.geopyspark.geotrellis.Json.writeHistogram(self.scala_histogram)
        return json.loads(histogram_json)
