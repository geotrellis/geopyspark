from collections import namedtuple


class Feature(namedtuple("Feature", "geometry properties")):
    """Represents a geometry that is derived from an OSM Element with that Element's associated metadata.

    Args:
        geometry (shapely.geometry): The geometry of the feature that is represented as
            a ``shapely.geometry``. This geometry is derived from an OSM Element.
        properties (:class:`~geopyspark.vector_pipe.Properties` or :class:`~geopyspark.vector_pipe.CellValue`):
            The metadata associated with the OSM Element. Can be represented as either an instance
            of ``Properties`` or a ``CellValue``.

    Attributes:
        geometry (shapely.geometry): The geometry of the feature that is represented as
            a ``shapely.geometry``. This geometry is derived from an OSM Element.
        properties (:class:`~geopyspark.vector_pipe.Properties` or :class:`~geopyspark.vector_pipe.CellValue`):
            The metadata associated with the OSM Element. Can be represented as either an instance
            of ``Properties`` or a ``CellValue``.
    """

    __slots__ = []


class Properties(namedtuple("Properties", "element_id user uid changeset version minor_version timestamp visible tags")):
    """Represents the metadata of an OSM Element.

    This object is one of two types that can be used to represent the ``properties`` of a
    :class:`~geopyspark.vector_pipe.Feature`.

    Args:
        element_id (int): The ``id`` of the OSM Element.
        user (str): The display name of the last user who modified/created the OSM Element.
        uid (int): The numeric id of the last user who modified the OSM Element.
        changeset (int): The OSM ``changeset`` number in which the OSM Element was created/modified.
        version (int): The edit version of the OSM Element.
        minor_version (int): Represents minor changes between versions of an OSM Element.
        timestamp (datetime.datetime): The time of the last modification to the OSM Element.
        visible (bool): Represents whether or not the OSM Element is deleted or not in the database.
        tags (dict): A ``dict`` of ``str``\s that represents the given features of the OSM Element.

    Attributes:
        element_id (int): The ``id`` of the OSM Element.
        user (str): The display name of the last user who modified/created the OSM Element.
        uid (int): The numeric id of the last user who modified the OSM Element.
        changeset (int): The OSM ``changeset`` number in which the OSM Element was created/modified.
        version (int): The edit version of the OSM Element.
        minor_version (int): Represents minor changes between versions of an OSM Element.
        timestamp (datetime.datetime): The time of the last modification to the OSM Element.
        visible (bool): Represents whether or not the OSM Element is deleted or not in the database.
        tags (dict): A ``dict`` of ``str``\s that represents the given features of the OSM Element.
    """

    __slots__ = []


class CellValue(namedtuple("CellValue", "value zindex")):
    """Represents the ``value`` and ``zindex`` of a geometry.

    This object is one of two types that can be used to represent the ``properties`` of a
    :class:`~geopyspark.vector_pipe.Feature`.

    Args:
        value (int or float): The value of all cells that intersects the associated geometry.
        zindex (int): The ``Z-Index`` of each cell that intersects the associated geometry.
            ``Z-Index`` determines which value a cell should be if multiple geometries
            intersect it. A high ``Z-Index`` will always be in front of a ``Z-Index`` of
            a lower value.

    Attributes:
        value (int or float): The value of all cells that intersects the associated geometry.
        zindex (int): The ``Z-Index`` of each cell that intersects the associated geometry.
            ``Z-Index`` determines which value a cell should be if multiple geometries
            intersect it. A high ``Z-Index`` will always be in front of a ``Z-Index`` of
            a lower value.
    """

    __slots__ = []


__all__ = ['Feature', 'Properties', 'CellValue']

from . import osm_reader

__all__ += ['osm_reader']
