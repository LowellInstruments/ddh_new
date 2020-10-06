import time
from datetime import datetime, timezone

import serial
from serial import SerialException

from mat.gps import GPS
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
        sig.gps_update_pos.emit(lat, lon)


def emit_gps_update_time_via(sig, via):
    if sig:
        sig.gps_update_time_via.emit(via)


def emit_gps_status(sig, s):
    if sig:
        sig.gps_status.emit(s)


def emit_gps_error(sig, e):
    if sig:
        sig.gps_error.emit(e)


# returns valid USB port or Exception
def _find_usb_gps():
    pat = {
        'linux': r'(ttyUSB(\d+))',
        'nt': r'^COM(\d+)',
    }
    try:
        # BU-353S4 GPS receiver: idVendor=067b, idProduct=2303
        dev = list(grep('067b:23[0909]'))[0][0]
    except (TypeError, IndexError, FileNotFoundError):
        return False
    p = pat.get(sys.platform)
    if not p:
        raise RuntimeError('SYS: unsupported OS ' + sys.platform)
    rv = re.search(p, dev).group(1)
    return rv


def _gps_pos_trim(f):
    # coordinates to 6 decimals
    lat, lon = None, None
    if f:
        lat = '{:8.6f}'.format(float(f.latitude))
        lon = '{:8.6f}'.format(float(f.longitude))
    return lat, lon


def _check_gps_hw_bu_353_s4(sig):
    p = _find_usb_gps()

    if p and sys.platform == 'linux':
        p = '/dev/{}'.format(p)
        with serial.Serial(p, 4800, timeout=10) as ser:
            if '$G'.encode() in ser.read(64):
                return True

    lat, lon = 'GPS hardware', 'malfunction'
    e = '{} {}'.format(lat, lon)
    emit_gps_error(sig, e)
    emit_gps_update_pos(sig, lat, lon)
    return False


def check_gps_hw(sig):
    # allows selecting different gps types
    return _check_gps_hw_bu_353_s4(sig)


def sync_pos(sig, timeout=10):
    f, p = gps_get_raw(timeout)
    lat, lon = _gps_pos_trim(f)

    # we have no port and no frame
    if not p:
        lat, lon = 'missing', 'missing'
        emit_gps_update_pos(sig, lat, lon)
        return
    else:
        # we have port but no frame
        if not f:
            lat, lon = 'searching', 'searching'
            emit_gps_update_pos(sig, lat, lon)
            return

    # we got frame, but incomplete one
    if not lat or not lon:
        e = 'corrupted GPS position'
        emit_gps_error(sig, e)
        return

    # we have port and frame
    emit_gps_update_pos(sig, lat, lon)
    return lat, lon


def _gps_sync_time(sig):
    f, _ = gps_get_raw()
    if f is None:
        e = 'GPS: got no frame'
        emit_gps_error(sig, e)
        emit_gps_update_time_via(sig, 'local')
        return False

    # GPS datetime object, UTC, no timezone info
    g_dt = f.timestamp

    # this is my timezone
    tz_utc = timezone.utc
    tz_me = get_localzone()

    # new datetime = gps datetime + apply timezone
    my_dt = g_dt.replace(tzinfo=tz_utc).astimezone(tz=tz_me)

    # between v3.6 and v3.7, let's do ours
    t = str(my_dt)[:-6]
    # print(my_time)

    # display result
    lat, lon = _gps_pos_trim(f)
    emit_gps_update_time_via(sig, 'GPS')
    emit_gps_update_pos(sig, lat, lon)
    linux_set_datetime(t)
    return True


# returns tuple(gps_tuple, usb_port)
def gps_get_raw(timeout=5) -> tuple:
    p = _find_usb_gps()
    if p and sys.platform == 'linux':
        # MAT library's gps w/ timeout
        p = '/dev/{}'.format(p)
        gps = GPS(p)
        return gps.get_gps_info(timeout), p
    return None, None


def gps_in_land(lat, lon):
    geoms = fiona.open(
        shpreader.natural_earth(resolution='50m',
                                category='physical', name='land'))
    land_geom = sgeom.MultiPolygon([sgeom.shape(geom['geometry'])
                                    for geom in geoms])
    land = prep(land_geom)
    # lon first
    return land.contains(sgeom.Point(float(lon), float(lat)))


def sync_time(sig):
    """ preferred NTP or RAW > GPS > local """
    # NTP
    if linux_is_net_ok():
        s = 'CLK: NTP-RAW sync'
        secs = get_ntp_time()
        # 1598537165 = 20/08/27 10:06:05 GMT-04:00
        if secs and secs > 1598537165:
            dt = datetime.fromtimestamp(secs)
            t = dt.strftime("%d %b %Y %H:%M:%S")
            if linux_set_datetime(t):
                emit_gps_status(sig, s)
                emit_gps_update_time_via(sig, 'NTP')
                return True

    # GPS: no NTP / internet or secs error
    rv = _gps_sync_time(sig)
    if rv:
        s = 'CLK: GPS sync'
        emit_gps_status(sig, s)
        emit_gps_update_time_via(sig, 'GPS')
        return True

    # we could only do local time
    s = 'CLK: using local'
    emit_gps_status(sig, s)
    return False


if __name__ == '__main__':
    while 1:
        sync_time(None)
