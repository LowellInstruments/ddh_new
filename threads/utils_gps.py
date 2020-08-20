from datetime import datetime, timedelta, timezone

import iso8601

from mat.gps import GPS
import re
import sys
from threads.utils import (
    linux_set_datetime, linux_is_net_ok, linux_rpi, get_ntp_time, linux_set_ntp)
from serial.tools.list_ports import grep
import time
import fiona
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom
from shapely.prepared import prep
from tzlocal import get_localzone


def emit_update(sig, rv, lat, lon):
    if sig:
        sig.gps_update.emit(rv, lat, lon)


def emit_error(sig, e):
    if sig:
        sig.gps_error.emit(e)


def emit_result(sig, via, when, lat, lon):
    if sig:
        sig.gps_result.emit(via, str(when), lat, lon)


def emit_status(sig, s):
    if sig:
        sig.gps_status.emit(s)


# returns valid USB port or Exception
def _find_usb_gps():
    port_patterns = {
        'linux': r'(ttyUSB(\d+))',
        'nt': r'^COM(\d+)',
    }
    try:
        # BU-353S4 GPS receiver: idVendor=067b, idProduct=2303
        dev = list(grep('067b:23[0909]'))[0][0]
    except (TypeError, IndexError, FileNotFoundError):
        return False
    p = port_patterns.get(sys.platform)
    if not p:
        raise RuntimeError('SYS: unsupported OS ' + sys.platform)
    return_value = re.search(p, dev).group(1)
    return return_value


def _gps_pos_trim(f):
    # coordinates to 6 decimals
    lat, lon = None, None
    if f:
        lat = '{:8.6f}'.format(float(f.latitude))
        lon = '{:8.6f}'.format(float(f.longitude))
    return lat, lon


def sync_pos(sig):
    f, p = gps_get_raw()
    lat, lon = _gps_pos_trim(f)

    # do we have port and frame
    if not p:
        s = 'GPS: missing'
        emit_update(sig, False, s, None)
        return
    else:
        s = 'GPS: USB device at {}'.format(p)
        emit_status(sig, s)
        if not f:
            s = 'GPS: searching'
            emit_update(sig, False, s, None)
            return

    # we got frame, but incomplete one
    if not lat or not lon:
        s = 'no lat, lon info in frame'
        emit_error(sig, s)
        return

    # we have port and frame
    emit_update(sig, True, lat, lon)
    return lat, lon


def _gps_sync_time(sig):
    f, _ = gps_get_raw()
    if f is None:
        e = 'GPS: got no frame'
        emit_error(sig, e)
        emit_result(sig, 'Local', None, None, None)
        return False

    # GPS datetime object, UTC, no timezone info
    g_dt = f.timestamp

    # this is my timezone
    tz_utc = timezone.utc
    tz_me = get_localzone()

    # new datetime = gps datetime + apply timezone
    my_dt = g_dt.replace(tzinfo=tz_utc).astimezone(tz=tz_me)

    # between v3.6 and v3.7, let's do ours
    my_time = str(my_dt)[:-6]
    # print(my_time)

    # display result
    lat, lon = str(f.latitude), str(f.longitude)
    emit_result(sig, 'GPS', my_time, lat, lon)

    linux_set_datetime(my_time)
    return True


# returns tuple(gps_tuple, usb_port)
def gps_get_raw(timeout=3) -> tuple:
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
        rv = None
        if linux_rpi():
            s = 'CLK: NTP sync'
            rv = linux_set_ntp()
        else:
            s = 'CLK: RAW sync'
            secs = get_ntp_time()
            if secs:
                dt = datetime.fromtimestamp(secs)
                t = dt.strftime("%d %b %Y %H:%M:%S")
                rv = linux_set_datetime(t)
        if rv:
            emit_status(sig, s)
            emit_result(sig, 'NTP', None, None, None)
            return

    # GPS since no NTP / internet
    rv = _gps_sync_time(sig)
    if rv:
        s = 'CLK: GPS sync'
        emit_status(sig, s)
        emit_result(sig, 'GPS', None, None, None)
    else:
        s = 'CLK: using local'
        emit_status(sig, s)


if __name__ == '__main__':
    _gps_sync_time(None)
