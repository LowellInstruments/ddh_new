from mat.gps import GPS
import time
import re
import sys
import pytz
from apps.ddh_utils import (
    linux_set_time_to_use_ntp,
    linux_set_time_from_gps,
    have_internet_connection
)
from serial.tools.list_ports import grep


class DeckDataHubGPS:

    @staticmethod
    def gps_loop(signals, ddh_gps_period):
        # force sync upon program / thread starts
        DeckDataHubGPS._gps_get_lan_n_lon(signals)
        DeckDataHubGPS._sync_sys_clock_gps_or_internet(signals)
        timeout_gps = ddh_gps_period

        while 1:
            if timeout_gps > 0:
                timeout_gps -= 1
            else:
                timeout_gps = ddh_gps_period
            if timeout_gps == 0:
                DeckDataHubGPS._sync_sys_clock_gps_or_internet(signals)
                DeckDataHubGPS._gps_get_lan_n_lon(signals)
            time.sleep(1)

    @staticmethod
    def _gps_get_lan_n_lon(signals):
        frame = DeckDataHubGPS._get_gps_frame(signals)
        if frame is None:
            # piggyback USB status in GPS error message
            signals.status.emit('GPS: could not obtain lat, lon.')
            t = 'No GPS\nin USB port'
            if find_port():
                t = 'Low GPS signal'
            signals.gps_update.emit(False, t, None)
            return

        # get coordinates to 6 decimals
        lat = '{:8.6f}'.format(float(frame.latitude))
        lon = '{:8.6f}'.format(float(frame.longitude))
        signals.status.emit('GPS: obtained lat, lon.')
        signals.gps_update.emit(True, lat, lon)

    # method to sync raspberry clock
    @staticmethod
    def _sync_sys_clock_gps_or_internet(signals):
        if have_internet_connection():
            status = 'SYS: internet, using NTP.'
            signals.status.emit(status)
            linux_set_time_to_use_ntp()
            signals.gps_result.emit('NTP', None, None, None)
            signals.internet_result.emit(True, '_')
        else:
            status = 'SYS: no internet, trying GPS...'
            signals.status.emit(status)
            # GPS receiver on USB but may receive frame in time, OR not
            DeckDataHubGPS._set_time_from_gps(signals)
            # what is sure is we don't have internet access
            signals.internet_result.emit(False, None)

    # sync system clock upon receiving GPRMC frame successfully
    @staticmethod
    def _set_time_from_gps(signals):
        # try to get GPS frame
        frame = DeckDataHubGPS._get_gps_frame(signals)
        if frame is None:
            signals.status.emit('GPS: no frame to sync time.')
            signals.gps_result.emit('Local', None, None, None)
            return False

        # set timezone in received datetime object and apply offset
        dt_utc = frame.timestamp
        dt_utc_zoned = dt_utc.astimezone(pytz.timezone('US/Eastern'))
        dt_est = str(dt_utc_zoned + dt_utc_zoned.utcoffset())[:19]
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

    # try getting GPRMC frame among all (GGA, GSA...)
    @staticmethod
    def _get_gps_frame(signals):
        usb_port = find_port()
        if usb_port:
            status = 'GPS: USB device at {}.'.format(usb_port)
            signals.status.emit(status)
            if sys.platform == 'linux':
                usb_port = '/dev/' + usb_port
            gps = GPS(usb_port)
            # try to get a gps RMC frame for some time or return None
            return gps.get_gps_info(3)
        else:
            status = 'GPS: no receiver found.'
            signals.status.emit(status)
            return None


# this guarantees either a valid USB port to operate on or an Exception
def find_port():
    port_patterns = {
        'linux': r'(ttyUSB(\d+))',
        'nt': r'^COM(\d+)',
    }
    try:
        # BU-353S4 GPS receiver: idVendor=067b, idProduct=2303
        field = list(grep('067b:23[0909]'))[0][0]
    except (TypeError, IndexError):
        return False
    pattern = port_patterns.get(sys.platform)
    if not pattern:
        raise RuntimeError('SYS: unsupported operating system: ' + sys.platform)
    return_value = re.search(pattern, field).group(1)
    return return_value
