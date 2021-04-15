import os
import sys
import time
from ddh.settings.ctx import dbg_hook_make_gps_give_fake_measurement
from ddh.threads.utils_gps_quectel import utils_gps_get_one_lat_lon_dt, utils_gps_cache_clear
from ddh.threads.utils_time import utils_time_update_datetime_source
from mat.gps_quectel import gps_configure_quectel
from mat.utils import linux_is_rpi


BOOT_GPS_FIX_TIMEOUT = 120


def _boot_sync_time(w):
    """ th_boot gets datetime source """

    utils_time_update_datetime_source(w)


def _boot_sync_position(w):
    """ th_boot gets first GPS position """

    t = BOOT_GPS_FIX_TIMEOUT
    _o = utils_gps_get_one_lat_lon_dt(t)
    w.sig_gps.update.emit(_o)


def _boot_connect_gps(w):

    # on Desktop, do not wait
    if not linux_is_rpi():
        w.lbl_ble.setText('no GPS shield to wait for')
        return

    # tries twice to enable GPS, used for position and time source
    if linux_is_rpi() and not dbg_hook_make_gps_give_fake_measurement:
        s = 'wait {}s for GPS fix'.format(BOOT_GPS_FIX_TIMEOUT)
        w.lbl_ble.setText(s)
        rv = gps_configure_quectel()
        if rv == 0:
            return
        time.sleep(1)
        rv = gps_configure_quectel()
        if rv:
            w.sig_boot.error.emit('SYS: boot error opening GPS port')
            os._exit(rv)
            sys.exit(rv)


def boot(w, evb):
    """ allows GUI to boot and does pre-threads things """

    # get first values ever for position and time and their sources
    time.sleep(.5)

    utils_gps_cache_clear()
    _boot_connect_gps(w)
    _boot_sync_time(w)
    _boot_sync_position(w)

    # now, allow other threads to boot
    w.sig_boot.status.emit('SYS: th_boot -> event_start other threads')
    evb.set()
