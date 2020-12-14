import time
from datetime import datetime, timezone
import serial
import re
import sys
from threads.utils import (
    linux_set_datetime, linux_is_net_ok, get_ntp_time)
from serial.tools.list_ports import grep
import fiona
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom
from shapely.prepared import prep
from tzlocal import get_localzone


def emit_gps_update_pos(sig, lat, lon):
    if sig:
        sig.update_pos.emit(lat, lon)


def emit_gps_update_time_via(sig, via):
    if sig:
        sig.update_time_via.emit(via)


def emit_gps_status(sig, s):
    if sig:
        sig.status.emit(s)


def emit_gps_error(sig, e):
    if sig:
        sig.error.emit(e)


def get_gps_lat_lon_more():
    # must return lat, lon, more, searching * 2, missing * 2 or corrupted on exception
    ts = time.perf_counter()
    return '12.34', '-55.23', ts


def gps_in_land(lat, lon):
    geoms = fiona.open(
        shpreader.natural_earth(resolution='50m',
                                category='physical', name='land'))
    land_geom = sgeom.MultiPolygon([sgeom.shape(geom['geometry'])
                                    for geom in geoms])
    land = prep(land_geom)
    # lon first
    return land.contains(sgeom.Point(float(lon), float(lat)))
