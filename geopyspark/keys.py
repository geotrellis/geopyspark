class SpatialKey(object):
    def __init__(self, col, row):
        self.col = col
        self.row = row

    def __repr__(self):
        return "SpatialKey(%d, %d)" % (self.col, self.row)


class SpaceTimeKey(object):
    def __init__(self, col, row, instant):
        self.col = col
        self.row = row
        self.instant = instant

    def __repr__(self):
        return "SpaceTimeKey(%d, %d, %d)" % (self.col, self.row, self.instant)
