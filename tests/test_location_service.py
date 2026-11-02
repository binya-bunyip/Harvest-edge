import struct

from geoalchemy2.elements import WKBElement

from harvest_edge.services.locations import _point_from_coordinates


def test_point_from_coordinates_creates_4326_ewkb_in_longitude_latitude_order() -> None:
    latitude, longitude = -33.8688, 151.2093

    point = _point_from_coordinates(latitude, longitude)

    assert isinstance(point, WKBElement)
    assert point.srid == 4326
    assert point.extended
    byte_order, geometry_type, srid, x, y = struct.unpack("<BIIdd", point.data)
    assert byte_order == 1
    assert geometry_type == 0x20000001
    assert srid == 4326
    assert (x, y) == (longitude, latitude)
