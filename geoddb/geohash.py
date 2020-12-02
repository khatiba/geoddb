"""
Geohash implementation using Gustavo Niemeyer's system: https://en.wikipedia.org/wiki/Geohash
"""


# geohash uses base32 to represent it's values: https://en.wikipedia.org/wiki/Geohash#Textual_representation
ghs32 = '0123456789bcdefghjkmnpqrstuvwxyz'


def bounds(geohash: str) -> ([float, float], [float, float]):
    """
    Get geohash lat/lon of the SW and NE corners

    Args:
        geohash: string, eg: 'ezs42'

    Raises:
        ValueError: if a character isn't found in the ghs32 set

    Returns:
        Two tuples of latitude min/max and longitude min/max of SW and NE corner
    """
    latRange = [-90, 90]
    lonRange = [-180, 180]

    bits = ''.join([format(ghs32.index(c), '05b') for c in geohash])

    for i, bit in enumerate(bits):
        if i % 2 == 0:
            lonMid = sum(lonRange)/2
            if bit == '1':
                lonRange[0] = lonMid
            else:
                lonRange[1] = lonMid
        else:
            latMid = sum(latRange)/2
            if bit == '1':
                latRange[0] = latMid
            else:
                latRange[1] = latMid

    return tuple(latRange), tuple(lonRange)


def encode(lat: float, lon: float, precision=12) -> str:
    """
    Generate geohash of length precision from float latitude and longitude

    Args:
        lat: float latitude
        lon: float longitude
        precision: length of geohash, see https://en.wikipedia.org/wiki/Geohash#Digits_and_precision_in_km

    Returns:
        geohash string
    """
    latRange = [-90, 90]
    lonRange = [-180, 180]

    geohash = ''
    char = 0b0

    for i in range(precision*5):
        if i % 2 == 0:
            lonMid = sum(lonRange)/2
            if lon >= lonMid:
                lonRange[0] = lonMid
                char = char << 1 | 1
            else:
                lonRange[1] = lonMid
                char = char << 1
        else:
            latMid = sum(latRange)/2
            if lat >= latMid:
                latRange[0] = latMid
                char = char << 1 | 1
            else:
                latRange[1] = latMid
                char = char << 1

        # 5 bits per character
        if (i+1) % 5 == 0:
            geohash += ghs32[int(bin(char), 2)]
            char = 0b0

    return geohash


def decode(geohash: str) -> (float, float):
    """
    Get latitude and longitude of geohash center

    Args:
        geohash: string, eg: 'ezs42'

    Raises:
        ValueError: if a character isn't found in the ghs32 set

    Returns:
        Two (lat, lon) pairs of geohash center
    """
    latRange, lonRange = bounds(geohash)
    center = sum(latRange)/2, sum(lonRange)/2
    return center


def neighbors(geohash: str) -> [str]:
    """
    Get surrounding neighbors of a geohash: N,NE,E,SE,S,SW,W,NW

    Args:
        geohash: string, eg: 'ezs42'

    Raises:
        ValueError: if a character isn't found in the ghs32 set

    Returns:
        list of geohash strings of all immediate surrounding cells
    """
    latRange, lonRange = bounds(geohash)
    lat, lon = sum(latRange)/2, sum(lonRange)/2
    latError = abs((latRange[1] - latRange[0])/2)
    lonError = abs((lonRange[1] - lonRange[0])/2)
    precision = len(geohash)

    neighbors = []
    neighbors.append(encode(lat + latError*2, lon             , precision)) # north
    neighbors.append(encode(lat + latError*2, lon + lonError*2, precision)) # north-east
    neighbors.append(encode(lat             , lon + lonError*2, precision)) # east
    neighbors.append(encode(lat - latError*2, lon + lonError*2, precision)) # south-east
    neighbors.append(encode(lat - latError*2, lon             , precision)) # south
    neighbors.append(encode(lat - latError*2, lon - lonError*2, precision)) # south-west
    neighbors.append(encode(lat             , lon - lonError*2, precision)) # west
    neighbors.append(encode(lat + latError*2, lon - lonError*2, precision)) # north-west

    return neighbors

