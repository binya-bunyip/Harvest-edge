from geoalchemy2.elements import WKTElement

from harvest_edge.services.locations import _point_from_coordinates


def test_point_from_coordinates_creates_4326_wkt_in_longitude_latitude_order() -> None:
    latitude, longitude = -33.8688, 151.2093

    point = _point_from_coordinates(latitude, longitude)

    assert isinstance(point, WKTElement)
    assert point.srid == 4326
    assert not point.extended
    assert point.data == f"POINT({longitude} {latitude})"
