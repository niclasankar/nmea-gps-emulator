#!/usr/bin/env python3

import time
import sys
import threading
import uuid
import logging
import math

from nmea_gps import NmeaMsg
from posutils import position_input, ip_port_input, trans_proto_input, heading_input, speed_input, heading_speed_input, serial_config_input
from custom_thread import NmeaStreamThread, NmeaSerialThread, run_telnet_server_thread

from pyproj import Geod
#import geopy.distance
#from geographiclib.geodesic import Geodesic, Constants

default_lon_pos = 11.987644320862213
defalt_lat_pos = 57.699193894531376
# 57.699193894531376, 11.987644320862213 Gbg
# 55.6061887051296, 13.0006314103057 Mme

def dec_to_dms(dec):
    # Convert from decimal degrees to DMS
    f,d = math.modf(dec)
    s,m = math.modf(abs(f) * 60)
    return (d,m,s * 60)

geod = Geodesic.WGS84

def main() -> None:

    # Use WGS84 ellipsoid.
    g = Geod(ellps='WGS84')
    print(g.a)
    # Forward transformation - returns longitude, latitude, back azimuth of terminus points
    #lon_end, lat_end, back_azimuth = g.fwd(default_lon_pos, defalt_lat_pos, 90, 1000)
    #print("pyproj lon: %s , lat: %s" % (lon_end, lat_end))

    #pt_end = geopy.distance.distance(meters=1000).destination((defalt_lat_pos, default_lon_pos), bearing=90)
    #print("geopy  lon: %s , lat: %s" % (pt_end.longitude, pt_end.latitude))
    #print(pt_end.format_decimal())

    # Direct(lat1, lon1, azi1, s12, outmask=1929)
    #glib_pt_end = geod.Direct(lat1 = defalt_lat_pos, lon1 = default_lon_pos, azi1 = 90, s12 = 1000, outmask=1929)
    #print("geographiclib ({:.10f}, {:.10f}).".format(glib_pt_end['lat2'],glib_pt_end['lon2']))
    #print(glib_pt_end)

    #print("Hello from nmea-gps-emulator!")
    return 0


main()

if __name__ == '__main__':
    # Logging config
    log_format = '%(asctime)s: %(message)s'
    logging.basicConfig(format=log_format, level=logging.INFO, datefmt='%H:%M:%S')

    #Menu().run()


