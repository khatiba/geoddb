import pytest
from geoddb.geohash import encode, decode, bounds, neighbors, haversine


class TestEncode:
    def test_known_geohash(self):
        # https://en.wikipedia.org/wiki/Geohash — example "ezs42" for (42.6, -5.6)
        result = encode(42.6, -5.6, precision=5)
        assert result == 'ezs42'

    def test_precision_length(self):
        for p in range(1, 13):
            assert len(encode(0, 0, p)) == p

    def test_origin(self):
        result = encode(0, 0, 5)
        assert isinstance(result, str)
        assert len(result) == 5

    def test_positive_coordinates(self):
        h = encode(48.8566, 2.3522, 7)  # Paris
        assert len(h) == 7

    def test_negative_coordinates(self):
        h = encode(-33.8688, 151.2093, 6)  # Sydney
        assert len(h) == 6

    def test_extreme_lat_lon(self):
        encode(90, 180, 5)
        encode(-90, -180, 5)

    def test_nearby_points_share_prefix(self):
        h1 = encode(40.7128, -74.0060, 5)  # NYC
        h2 = encode(40.7130, -74.0058, 5)  # very close
        assert h1 == h2


class TestDecode:
    def test_decode_roundtrip(self):
        lat, lon = 42.6, -5.6
        h = encode(lat, lon, 5)
        dlat, dlon = decode(h)
        # With precision 5, error is within ~2.4km
        assert abs(dlat - lat) < 0.1
        assert abs(dlon - lon) < 0.1

    def test_decode_known(self):
        lat, lon = decode('ezs42')
        assert abs(lat - 42.6) < 0.1
        assert abs(lon - (-5.6)) < 0.1

    def test_decode_returns_tuple(self):
        result = decode('u4pruydqqvj')
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestBounds:
    def test_bounds_returns_two_tuples(self):
        lat_range, lon_range = bounds('ezs42')
        assert len(lat_range) == 2
        assert len(lon_range) == 2

    def test_bounds_lat_range_ordered(self):
        lat_range, lon_range = bounds('ezs42')
        assert lat_range[0] < lat_range[1]
        assert lon_range[0] < lon_range[1]

    def test_bounds_contain_decoded_center(self):
        h = encode(40.7128, -74.0060, 6)
        lat_range, lon_range = bounds(h)
        lat, lon = decode(h)
        assert lat_range[0] <= lat <= lat_range[1]
        assert lon_range[0] <= lon <= lon_range[1]

    def test_invalid_character_raises(self):
        with pytest.raises(ValueError):
            bounds('aaaa')  # 'a' is not in ghs32


class TestNeighbors:
    def test_returns_8_neighbors(self):
        result = neighbors('ezs42')
        assert len(result) == 8

    def test_neighbors_are_same_precision(self):
        h = 'ezs42'
        for n in neighbors(h):
            assert len(n) == len(h)

    def test_neighbors_are_unique(self):
        result = neighbors('ezs42')
        assert len(set(result)) == 8

    def test_center_not_in_neighbors(self):
        h = 'ezs42'
        assert h not in neighbors(h)

    def test_neighbor_contains_adjacent_cell(self):
        h = encode(40.7128, -74.0060, 5)
        nbrs = neighbors(h)
        # Each neighbor should decode to a nearby location
        center_lat, center_lon = decode(h)
        for n in nbrs:
            nlat, nlon = decode(n)
            dist = haversine(center_lat, center_lon, nlat, nlon)
            # Neighbors should be relatively close (within a few hundred km for precision 5)
            assert dist < 500


class TestHaversine:
    def test_same_point_is_zero(self):
        assert haversine(0, 0, 0, 0) == 0.0

    def test_known_distance(self):
        # NYC to LA ~ 3944 km
        dist = haversine(40.7128, -74.0060, 34.0522, -118.2437)
        assert 3900 < dist < 4000

    def test_symmetric(self):
        d1 = haversine(40.7128, -74.0060, 48.8566, 2.3522)
        d2 = haversine(48.8566, 2.3522, 40.7128, -74.0060)
        assert abs(d1 - d2) < 1e-9

    def test_antipodal_points(self):
        # Opposite ends of the earth ~ half circumference ~ 20015 km
        dist = haversine(0, 0, 0, 180)
        assert 20000 < dist < 20100

    def test_poles(self):
        dist = haversine(90, 0, -90, 0)
        assert 20000 < dist < 20100
