# GeoDDB - Geohashing in DynamoDB

GeoDDB is a simple Python module that lets you store and query your location data in DynamoDB. This module does _not_ require creating a new table with local secondary indexes or global secondary indexes. Just tell GeoDDB the name of your partition key and point it to a DynamoDB table. This module also comes with it's own [Geohash](https://en.wikipedia.org/wiki/Geohash) implementation, so the only dependency is [boto3](https://github.com/boto/boto3).

