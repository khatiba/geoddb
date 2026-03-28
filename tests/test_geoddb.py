import pytest
from unittest.mock import MagicMock, patch, call
from dataclasses import asdict
from geoddb.geoddb import GeoDDB, GeoItem
from geoddb.geohash import encode


@pytest.fixture
def mock_table():
    return MagicMock()


@pytest.fixture
def geo(mock_table):
    return GeoDDB(table=mock_table, pk_name='pk', precision=5)


@pytest.fixture
def geo_with_prefix(mock_table):
    return GeoDDB(table=mock_table, pk_name='pk', precision=5, prefix='GEO#')


class TestGeoItem:
    def test_default_data(self):
        item = GeoItem(lat=1.0, lon=2.0, distance_km=0.5, geohash='abc')
        assert item.data == {}

    def test_with_data(self):
        item = GeoItem(lat=1.0, lon=2.0, distance_km=0.5, geohash='abc', data={'name': 'x'})
        assert item.data == {'name': 'x'}

    def test_is_dataclass(self):
        item = GeoItem(lat=1.0, lon=2.0, distance_km=0.5, geohash='abc')
        d = asdict(item)
        assert d['lat'] == 1.0
        assert d['geohash'] == 'abc'


class TestGetPkValue:
    def test_no_prefix(self, geo):
        assert geo.get_pk_value('ezs42') == 'ezs42'

    def test_with_prefix(self, geo_with_prefix):
        assert geo_with_prefix.get_pk_value('ezs42') == 'GEO#ezs42'


class TestPutItem:
    def test_calls_put_item_on_table(self, geo, mock_table):
        mock_table.put_item.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}}

        data = {'name': 'cafe', 'lat': 40.7128, 'lon': -74.0060}
        result = geo.put_item(40.7128, -74.0060, data)

        mock_table.put_item.assert_called_once()
        call_kwargs = mock_table.put_item.call_args
        item = call_kwargs[1]['Item'] if 'Item' in call_kwargs[1] else call_kwargs[0][0]
        assert 'pk' in item
        assert item['name'] == 'cafe'

    def test_geohash_overwrites_user_pk(self, geo, mock_table):
        mock_table.put_item.return_value = {}
        data = {'pk': 'should-be-overwritten', 'name': 'test'}
        geo.put_item(40.7128, -74.0060, data)

        call_kwargs = mock_table.put_item.call_args
        item = call_kwargs[1]['Item']
        expected_hash = encode(40.7128, -74.0060, 5)
        assert item['pk'] == expected_hash

    def test_with_prefix(self, geo_with_prefix, mock_table):
        mock_table.put_item.return_value = {}
        geo_with_prefix.put_item(40.7128, -74.0060, {'name': 'test'})

        item = mock_table.put_item.call_args[1]['Item']
        assert item['pk'].startswith('GEO#')

    def test_forwards_ddb_kwargs(self, geo, mock_table):
        mock_table.put_item.return_value = {}
        geo.put_item(40.7128, -74.0060, {'name': 'test'},
                     ddb_kwargs={'ConditionExpression': 'attribute_not_exists(pk)'})

        call_kwargs = mock_table.put_item.call_args
        assert 'ConditionExpression' in call_kwargs[1]

    def test_does_not_mutate_input_data(self, geo, mock_table):
        mock_table.put_item.return_value = {}
        data = {'name': 'test'}
        geo.put_item(40.7128, -74.0060, data)
        assert 'pk' not in data


class TestDeleteItem:
    def test_calls_delete_item(self, geo, mock_table):
        mock_table.delete_item.return_value = {}
        geo.delete_item(40.7128, -74.0060, 'sk', 'item-1')

        mock_table.delete_item.assert_called_once()
        key = mock_table.delete_item.call_args[1]['Key']
        expected_hash = encode(40.7128, -74.0060, 5)
        assert key['pk'] == expected_hash
        assert key['sk'] == 'item-1'

    def test_forwards_ddb_kwargs(self, geo, mock_table):
        mock_table.delete_item.return_value = {}
        geo.delete_item(40.7128, -74.0060, 'sk', 'item-1',
                        ddb_kwargs={'ReturnValues': 'ALL_OLD'})

        assert 'ReturnValues' in mock_table.delete_item.call_args[1]


class TestQuery:
    def test_queries_center_and_neighbors(self, geo, mock_table):
        mock_table.query.return_value = {'Items': []}
        geo.query(40.7128, -74.0060, include_neighbors=True)

        # 1 center + 8 neighbors = 9 queries
        assert mock_table.query.call_count == 9

    def test_queries_center_only(self, geo, mock_table):
        mock_table.query.return_value = {'Items': []}
        geo.query(40.7128, -74.0060, include_neighbors=False)

        assert mock_table.query.call_count == 1

    def test_returns_items(self, geo, mock_table):
        mock_table.query.return_value = {'Items': [{'name': 'cafe'}]}
        results = geo.query(40.7128, -74.0060, include_neighbors=False)

        assert len(results) == 1
        assert results[0]['name'] == 'cafe'

    def test_aggregates_items_from_multiple_hashes(self, geo, mock_table):
        mock_table.query.return_value = {'Items': [{'id': '1'}]}
        results = geo.query(40.7128, -74.0060, include_neighbors=True)

        # 9 queries each returning 1 item
        assert len(results) == 9

    def test_pagination(self, geo, mock_table):
        mock_table.query.side_effect = [
            {'Items': [{'id': '1'}], 'LastEvaluatedKey': {'pk': 'x'}},
            {'Items': [{'id': '2'}]},
        ]
        results = geo.query(40.7128, -74.0060, include_neighbors=False, include_all_pages=True)

        assert len(results) == 2
        assert mock_table.query.call_count == 2

    def test_no_pagination_when_disabled(self, geo, mock_table):
        mock_table.query.return_value = {
            'Items': [{'id': '1'}],
            'LastEvaluatedKey': {'pk': 'x'},
        }
        results = geo.query(40.7128, -74.0060, include_neighbors=False, include_all_pages=False)

        assert len(results) == 1
        assert mock_table.query.call_count == 1

    def test_extra_key_condition(self, geo, mock_table):
        from boto3.dynamodb.conditions import Key
        mock_table.query.return_value = {'Items': []}
        geo.query(40.7128, -74.0060, include_neighbors=False,
                  ddb_kwargs={'KeyConditionExpression': Key('sk').begins_with('CAFE#')})

        call_kwargs = mock_table.query.call_args[1]
        # The key condition should be combined (& operator)
        assert 'KeyConditionExpression' in call_kwargs


class TestQueryRadius:
    def test_filters_by_distance(self, geo, mock_table):
        center_lat, center_lon = 40.7128, -74.0060
        # Return near item only from center hash, far item from a neighbor
        near_items = {'Items': [{'lat': 40.7130, 'lon': -74.0058, 'name': 'near'}]}
        far_items = {'Items': [{'lat': 41.5, 'lon': -73.0, 'name': 'far'}]}
        empty = {'Items': []}
        mock_table.query.side_effect = [near_items, far_items] + [empty] * 7
        results = geo.query_radius(center_lat, center_lon, radius_km=1.0)

        assert len(results) == 1
        assert results[0].data['name'] == 'near'

    def test_returns_geo_items(self, geo, mock_table):
        items = {'Items': [{'lat': 40.7130, 'lon': -74.0058}]}
        empty = {'Items': []}
        mock_table.query.side_effect = [items] + [empty] * 8
        results = geo.query_radius(40.7128, -74.0060, radius_km=10.0)

        assert len(results) == 1
        assert isinstance(results[0], GeoItem)
        assert results[0].distance_km >= 0

    def test_sorted_nearest_first(self, geo, mock_table):
        center_lat, center_lon = 40.7128, -74.0060
        mock_table.query.return_value = {'Items': [
            {'lat': 40.72, 'lon': -74.01, 'name': 'medium'},
            {'lat': 40.7129, 'lon': -74.0061, 'name': 'closest'},
            {'lat': 40.73, 'lon': -74.02, 'name': 'farthest'},
        ]}
        results = geo.query_radius(center_lat, center_lon, radius_km=50.0)

        distances = [r.distance_km for r in results]
        assert distances == sorted(distances)

    def test_custom_lat_lon_attrs(self, geo, mock_table):
        items = {'Items': [{'latitude': 40.7130, 'longitude': -74.0058}]}
        empty = {'Items': []}
        mock_table.query.side_effect = [items] + [empty] * 8
        results = geo.query_radius(40.7128, -74.0060, radius_km=10.0,
                                   lat_attr='latitude', lon_attr='longitude')
        assert len(results) == 1

    def test_empty_results(self, geo, mock_table):
        mock_table.query.return_value = {'Items': []}
        results = geo.query_radius(40.7128, -74.0060, radius_km=1.0)
        assert results == []

    def test_geo_item_has_correct_geohash(self, geo, mock_table):
        mock_table.query.return_value = {'Items': [
            {'lat': 40.7130, 'lon': -74.0058},
        ]}
        results = geo.query_radius(40.7128, -74.0060, radius_km=10.0)

        expected_hash = encode(40.7130, -74.0058, 5)
        assert results[0].geohash == expected_hash
