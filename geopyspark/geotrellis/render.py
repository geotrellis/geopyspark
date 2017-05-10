from PIL import Image


class PngRDD(object):
    def __init__(self, geopysc, rdd_type, srdd, color_map):
        self.geopysc = geopysc
        self.rdd_type = rdd_type
        self.srdd = srdd.map(color_map)
        self.color_map = color_map

    def lookup(self, col, row):
        """Return the value(s) in the image of a particular SpatialKey (given by col and row)

        Args:
            col (int): The SpatialKey column
            row (int): The SpatialKey row

        Returns: An array of numpy arrays (the tiles)
        """
        bounds = self.layer_metadata['bounds']
        min_col = bounds['minKey']['col']
        min_row = bounds['minKey']['row']
        max_col = bounds['maxKey']['col']
        max_row = bounds['maxKey']['row']

        if col < min_col or col > max_col:
            raise IndexError("column out of bounds")
        if row < min_row or row > max_row:
            raise IndexError("row out of bounds")

        arrays = self.srdd.lookup(col, row)

        if self.color_map.has_alpha():
            return [Image.fromarray(arr, 'RGBA') for arr in arrays]
        else:
            return [Image.fromarray(arr, 'RGB') for arr in arrays]
