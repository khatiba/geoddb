from boto3.dynamodb.conditions import Key
from boto3.dynamodb.table import TableResource
from .geohash import encode, neighbors


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
            key_condition_expression = Key('PK').eq(self.get_pk_value(hash))
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

