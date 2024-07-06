#!/usr/bin/env python3

import time
import sys
import threading
import uuid
import logging

from pyproj import Geod
import geopy.distance
from geographiclib.geodesic import Geodesic, Constants

lon_start = 11.987644320862213
lat_start = 57.699193894531376
# 57.699193894531376, 11.987644320862213
# 55.6061887051296, 13.0006314103057

geod = Geodesic.WGS84

def main() -> int:

    # Use WGS84 ellipsoid.
    g = Geod(ellps='WGS84')
    # Forward transformation - returns longitude, latitude, back azimuth of terminus points
    lon_end, lat_end, back_azimuth = g.fwd(lon_start, lat_start, 90, 1000)
    print("pyproj lon: %s , lat: %s" % (lon_end, lat_end))

    pt_end = geopy.distance.distance(meters=1000).destination((lat_start, lon_start), bearing=90)
    print("geopy  lon: %s , lat: %s" % (pt_end.longitude, pt_end.latitude))
    #print(pt_end.format_decimal())

    # Direct(lat1, lon1, azi1, s12, outmask=1929)
    glib_pt_end = geod.Direct(lat1 = lat_start, lon1 = lon_start, azi1 = 90, s12 = 1000, outmask=1929)
    print("geographiclib ({:.10f}, {:.10f}).".format(glib_pt_end['lat2'],glib_pt_end['lon2']))
    #print(glib_pt_end)

    #print("Hello from nmea-gps-emulator!")
    return 0


main()