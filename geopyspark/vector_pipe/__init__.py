from collections import namedtuple


Feature = namedtuple("Feature", "geometry properties")

Properties = namedtuple("Properties", "element_id user uid changeset version minor_version timestamp visible tags")
