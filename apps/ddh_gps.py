from mat.gps import GPS
import datetime
import time
import re
import sys
import pytz
from apps.ddh_utils import (
    linux_set_time_to_use_ntp,
    linux_set_time_from_gps,
    linux_have_internet_connection
)
from serial.tools.list_ports import grep


class DeckDataHubGPS:

    GPS_PERIOD = 30
    GPS_FRESH_HOLD = 30
    gps_last = [None, None, None]

    @staticmethod
    def gps_loop(signals, ddh_gps_period):
        # force sync upon program / thread starts
        ddh_gps._gps_get_lat_n_lon(signals)
        ddh_gps._sync_sys_clock_gps_or_internet(signals)
        gps_timeout = ddh_gps_period

        while 1:
            if gps_timeout > 0:
                gps_timeout -= 1
            else:
                gps_timeout = ddh_gps_period
            if gps_timeout == 0:
                ddh_gps._sync_sys_clock_gps_or_internet(signals)
                ddh_gps._gps_get_lat_n_lon(signals)
            time.sleep(1)

    # try getting GPRMC frame among all (GGA, GSA...)
    @staticmethod
    def _get_gps_frame(signals):
        usb_port = find_port()
        if usb_port:
            status = 'GPS: USB device at {}'.format(usb_port)
            signals.status.emit(status)
            if sys.platform == 'linux':
                usb_port = '/dev/' + usb_port
            gps = GPS(usb_port)
            # MAT library gets a gps RMC frame w/ timeout or return None
            return gps.get_gps_info(3)
        else:
            return None

    @staticmethod
    def _gps_get_lat_n_lon(signals):
        ddh_gps.gps_last = [None, None, None]
        frame = ddh_gps._get_gps_frame(signals)

        # no frame at all, piggyback USB status in error message
        if frame is None:
            t = 'GPS: missing'
            if find_port():
                t = 'GPS: searching'
            signals.gps_update.emit(False, t, None)
            return

        # frame, but an incomplete one
        if not frame.latitude or not frame.longitude:
            t = 'No lat, lon info in frame'
            signals.error.emit(False, t, None)
            return

        # get coordinates to 6 decimals
        lat = '{:8.6f}'.format(float(frame.latitude))
        lon = '{:8.6f}'.format(float(frame.longitude))
        ddh_gps.gps_last = [lat, lon, datetime.datetime.now()]
        signals.status.emit('GPS: got lat, lon')
        signals.gps_update.emit(True, lat, lon)

    @staticmethod
    def _gps_is_fresh(t):
        if not t:
            return False
        n = datetime.datetime.now()
        if (n - t).seconds < ddh_gps.GPS_FRESH_HOLD:
            return True
        return False

    @staticmethod
    def gps_get_last(signals):
        # gps_last updated in _gps_get_lat_n_lon
        g = ddh_gps.gps_last
        t = g[2]
        lat, lon = None, None
        if ddh_gps._gps_is_fresh(t):
            signals.status.emit('GPS: is fresh {}'.format(t))
            lat, lon = g[0], g[1]
        return lat, lon

    # method to sync raspberry clock
    @staticmethod
    def _sync_sys_clock_gps_or_internet(signals):
        if linux_have_internet_connection():
            status = 'GPS: using NTP time'
            signals.status.emit(status)
            linux_set_time_to_use_ntp()
            signals.gps_result.emit('NTP', None, None, None)
            signals.internet_result.emit(True, '_')
        else:
            status = 'GPS: no NTP, waiting for sat frame'
            signals.status.emit(status)
            # GPS receiver on USB but may receive frame in time, OR not
            ddh_gps._set_time_from_gps(signals)
            # what is sure is we don't have internet access
            signals.internet_result.emit(False, None)

    # sync system clock upon receiving GPRMC frame successfully
    @staticmethod
    def _set_time_from_gps(signals):
        # try to get GPS frame
        frame = ddh_gps._get_gps_frame(signals)
        if frame is None:
            signals.status.emit('GPS: no frame to sync time')
            signals.gps_result.emit('Local', None, None, None)
            return False

        # set timezone in received datetime object and apply offset
        # dt_utc = frame.timestamp
        # dt_utc_zoned = dt_utc.astimezone(pytz.timezone('US/Eastern'))
        # dt_est = str(dt_utc_zoned + dt_utc_zoned.utcoffset())[:19]

        # UTC time adjusted to our timezone offset
        off = -time.timezone
        dt_est = str(frame.timestamp + datetime.timedelta(seconds=off))

        # display results
        lat, lon = str(frame.latitude), str(frame.longitude)
        signals.gps_result.emit('GPS', dt_est, lat, lon)

        # build tuple for linux commands (Y,M,D,H,M,S,ms) and set local time
        time_tuple = (int(dt_est[0:4]),
                      int(dt_est[5:7]),
                      int(dt_est[8:10]),
                      int(dt_est[11:13]),
                      int(dt_est[14:16]),
                      int(dt_est[17:19]),
                      00,
                      )

        linux_set_time_from_gps(time_tuple)
        return True


# this guarantees either a valid USB port to operate on or an Exception
def find_port():
    port_patterns = {
        'linux': r'(ttyUSB(\d+))',
        'nt': r'^COM(\d+)',
    }
    try:
        # BU-353S4 GPS receiver: idVendor=067b, idProduct=2303
        field = list(grep('067b:23[0909]'))[0][0]
    except (TypeError, IndexError, FileNotFoundError):
        return False
    pattern = port_patterns.get(sys.platform)
    if not pattern:
        raise RuntimeError('SYS: unsupported OS ' + sys.platform)
    return_value = re.search(pattern, field).group(1)
    return return_value


# shorten name
ddh_gps = DeckDataHubGPS
