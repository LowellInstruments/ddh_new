import time
from datetime import datetime, timezone
import serial
import re
import sys

from mat.gps_quectel import gps_parse_rmc_frame, PORT_DATA, enable_gps_output
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


def get_gps_lat_lon_more(timeout=3):
    _till = time.perf_counter() + timeout
    enable_gps_output()
    print('GPS Quectel receiving...')
    sp = serial.Serial(PORT_DATA, baudrate=115200, timeout=0.5)

    while True:
        if time.perf_counter() > _till:
            break
        data = sp.readline()
        if '$GPRMC' in data:
            if gps_parse_rmc_frame(data):
                return g
    return None


def gps_in_land(lat, lon):
    geoms = fiona.open(
        shpreader.natural_earth(resolution='50m',
                                category='physical', name='land'))
    land_geom = sgeom.MultiPolygon([sgeom.shape(geom['geometry'])
                                    for geom in geoms])
    land = prep(land_geom)
    # lon first
    return land.contains(sgeom.Point(float(lon), float(lat)))
