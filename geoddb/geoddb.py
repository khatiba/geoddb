from boto3.dynamodb.conditions import Key
from boto3.dynamodb.table import TableResource
from .geohash import encode, neighbors, haversine


class GeoDDB:

    def __init__(self, table: TableResource, pk_name: str, precision: int, prefix=''):
        self.table = table
        self.pk_name = pk_name
        self.precision = precision
        self.prefix = prefix

    def get_pk_value(self, geohash: str) -> str:
        return f'{self.prefix}{geohash}'

    def put_item(self, lat: float, lon: float, data: dict, ddb_kwargs=None) -> dict:
        if not ddb_kwargs:
            ddb_kwargs = {}

        item = {}
        item.update(data)

        # add the hash key _after_ in case the user mistakenly includes one
        geohash = encode(lat, lon, self.precision)
        item[self.pk_name] = self.get_pk_value(geohash)

        return self.table.put_item(Item=item, **ddb_kwargs)

    def query(self, lat: float, lon: float, include_neighbors=True, include_all_pages=True, ddb_kwargs=None) -> [dict]:
        if not ddb_kwargs:
            ddb_kwargs = {}

        current_hash = encode(lat, lon, self.precision)

        hashes = [current_hash]
        if include_neighbors:
            hashes += neighbors(current_hash)

        # pop from ddb_kwargs here to combine with partition key condition later
        extra_key_condition = ddb_kwargs.pop('KeyConditionExpression', None)

        results = []
        for hash in hashes:
            key_condition_expression = Key(self.pk_name).eq(self.get_pk_value(hash))
            if extra_key_condition:
                key_condition_expression &= extra_key_condition

            resp = self.table.query(KeyConditionExpression=key_condition_expression, **ddb_kwargs)
            results += resp['Items']

            if include_all_pages:
                # exhaustively walk all results if paginated
                while 'LastEvaluatedKey' in resp:
                    resp = self.table.query(KeyConditionExpression=key_condition_expression, ExclusiveStartKey=resp['LastEvaluatedKey'], **ddb_kwargs)
                    results += resp['Items']

        return results

    def query_radius(self, lat: float, lon: float, radius_km: float,
                     lat_attr='lat', lon_attr='lon',
                     include_all_pages=True, ddb_kwargs=None) -> [dict]:
        """
        Query items within a radius (km) of a point, filtered by Haversine distance
        and sorted nearest-first. Each returned item has a '_distance_km' key added.

        Args:
            lat: query center latitude
            lon: query center longitude
            radius_km: maximum distance in kilometers
            lat_attr: name of the latitude attribute stored in items
            lon_attr: name of the longitude attribute stored in items
            include_all_pages: exhaust DynamoDB pagination
            ddb_kwargs: extra kwargs forwarded to table.query()

        Returns:
            list of items within the radius, sorted by distance, each with '_distance_km'
        """
        items = self.query(lat, lon, include_neighbors=True,
                           include_all_pages=include_all_pages, ddb_kwargs=ddb_kwargs)

        results = []
        for item in items:
            item_lat = float(item[lat_attr])
            item_lon = float(item[lon_attr])
            dist = haversine(lat, lon, item_lat, item_lon)
            if dist <= radius_km:
                item['_distance_km'] = round(dist, 6)
                results.append(item)

        results.sort(key=lambda x: x['_distance_km'])
        return results

