# GeoDDB - Geohash in DynamoDB

GeoDDB is a simple Python module that helps you store and query your location data in DynamoDB using just the partition key, without requiring any changes to your existing table or indexes.


## Getting Started

- GeoDDB does _not_ require a new or separate table, you should create a table if you don't already have one
    - For more information on single-table design refer to Rick Houlihan's re:Invent talk on [Advanced design patterns with DynamoDB](https://www.youtube.com/watch?v=6yqfmXiZTlM) and his [other talk](https://www.youtube.com/watch?v=KYy8X8t4MB8) specifically on single-table design. See also re:Invent 2020 talks by [Alex DeBrie](https://www.alexdebrie.com) on data modeling in DynamoDB [Part 1](https://virtual.awsevents.com/media/1_8sijtjhh) and [Part 2](https://virtual.awsevents.com/media/1_2dvdhgl7).
- GeoDDB does _not_ create or require local secondary indexes or global secondary indexes
    - You can certainly use LSIs and/or GSIs but this module doesn't require them
- GeoDDB does _not_ require a sort/range key, just tell it the name of your partition key
    - This avoids interfering with your ability to use composite keys to satisfy other access patterns


### Installation
This package comes with its own [Geohash](https://en.wikipedia.org/wiki/Geohash) implementation, so the only dependency is [boto3](https://github.com/boto/boto3).
```bash
pip install geoddb
```

## Examples

### Adding an Item
```python
import boto3
from geoddb import GeoDDB

ddb = boto3.resource('dynamodb')
table = ddb.Table('FooTable')

gddb = GeoDDB(table, pk_name='PK', precision=5)

lat, lon = 33.63195443030888, -117.93583128993387

data = { 
    'SK': f'coffee#daydream',  # SK is my sort key, note that no partition key is present
    'Name': 'Daydream',
    'EntityType': 'Coffee/Surf Shop',
    'Address': '1588 Monrovia Ave, Newport Beach, CA 92663'
}

gddb.put_item(lat, lon, data)
```

Here we add a location with geohash length of 5, so the cell dimension is about 5km x 5km (3mi x 3mi).


### Searching Items
```python
import boto3
from geoddb import GeoDDB

ddb = boto3.resource('dynamodb')
table = ddb.Table('FooTable')

# use same settings here as when you added the location
gddb = GeoDDB(table, pk_name='PK', precision=5)

myLat, myLon = 33.66677439489231, -118.01282517173841

results = gddb.query(myLat, myLon, ddb_kwargs={
    'KeyConditionExpression': Key('SK').begins_with('coffee#'),
})
```

Here we search for coffee around a point of interest (my current location for example). Note that the same settings are used for querying that were used when storing the data. These settings can change for different collections of data, but must be consistent when storing and querying within the same set of data.

## Options

### DynamoDB Arguments
```python
gddb.query(myLat, myLon, ddb_kwargs={
  'Limit': 10,
  'KeyConditionExpression': Key('SK').begins_with('coffee#'),
  'FilterExpression': Attr('Rating').gt(4.5)
})
```

GeoDDB's `put_item` and `query` accept a `ddb_kwargs` argument where you can include extra DynamoDB specific arguments. Note you should _not_ include a condition on your partition key, this is handled by GeoDDB.


### Geohash Prefix
```python
gddb = GeoDDB(table, pk_name='PK', precision=5, prefix='loc#')
```

GeoDDB uses the geohash of a location as the partition key for your item, you can prefix this string if needed, for example `loc#` or `geohash#`.
 This would result in `loc#` followed by the geohash, eg: `loc#7mup6`. This can be useful for example in single-table design where key-blending is necessary.


### Neighboring Cells
```python
gddb.query(myLat, myLon, include_neighbors=False)
```

By default, all neighbors of your input geohash are queried. This is to avoid situations where the query location is near the edge of a cell and nearby results in the next cell would be missing. You may include or exclude neighboring cells depending on your use-case but no more than 9 cells are ever queried. You can turn this off:


### Walk All Pages
```python
gddb.query(myLat, myLon, include_all_pages=False)
```

By default, GeoDDB will walk all pages of results and return a complete list of items. Depending on your use-case and geohash length, this can lead to memory issues. You can turn this off:


## Limitations

### Bring Your Own Table
GeoDDB does not require, nor will it create a separate table or additional indexes for you. This was the **biggest** motivation for this project. Most of the time, a table already exists with appropriate indexes to satisfy a set of access patterns. This is especially true in a single-table design where composite keys are usually required and you need the sort key to filter collections items within a partition. I don't want to have to create a new table with local secondary indexes or use up a precious global secondary index when the whole benefit of geohashing is the ability to do a single lookup! You can certainly add a GSI if your application requires it to satisfy an access pattern, but the minimum needed for geohash queries is a partition key.


### Radius Filtering
Filtering results by an arbitrary radius is not supported. Geohashes are rectangular and their sizes depend on your chosen precision. Consider controlling results with an appropriate choice of geohash length. At most nine (9) queries are executed and return results within a 3x3 rectangle containing your geohash and its neighbors. Choose your geohash precision so that your desired query range is within the corresponding cell dimensions. This will ensure that results lie within at least 1 cell size from the search point. See [table](#geohash-cell-dimensions) of geohash length and rectangular dimensions.

You can of course use the [Haversine formula](https://en.wikipedia.org/wiki/Haversine_formula) to calculate accurate great circle distance and filter in your application. For small distances, a better performing approximation using an [equirectangular projection](https://en.wikipedia.org/wiki/Equirectangular_projection) might also be suitable. Note again, at most 9 cells are queried, so your radius of interest shouldn't be larger than the shortest side of the 3x3 cell rectangle.

You may also set different geohash lengths for different types of your location data. For example: a 5 character long geohash is probably okay for coffee shop searches but not for airports where 3-4 characters might be more appropriate.


### Updating a Location
This should be an infrequent operation. Obviously since the geohash is generated from the latitude and longitude of the location, in general you can't simply change those values without changing the geohash. Since you can't change the partition key of an item in DynamoDB, you must first delete the record and create a new record. This package doesn't come with any helpers to do this since finding the specific item to delete and re-add depends on your data structure.


## Geohash Cell Dimensions
Cell dimensions change with latitude, these are approximate. 

|  Length  |  Width x Height    |
|  ---             |  ---               |
|  1               |  5,009km x 4,992km |
|  2               |  1,252km x 624km   |
|  3               |  156km x 156km     |
|  4               |  39.1km x 19.5km   |
|  5               |  4.9km x 4.9km     |
|  6               |  1.2km x 609.4m    |
|  7               |  152.9m x 152.4m   |
|  8               |  38.2m x 19m       |
|  9               |  4.8m x 4.8m       |
|  10              |  1.2m x 59.5cm     |
|  11              |  14.9cm x 14.9cm   |
|  12              |  3.7cm x 1.9cm     |




# Bugs?!
Maybe... Probably, I don't have any tests yet :/

