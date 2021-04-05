import os
import sys
import time
from ddh.settings.ctx import dbg_hook_make_gps_give_fake_measurement
from ddh.threads.utils_gps_quectel import utils_gps_get_one_lat_lon_dt
from ddh.threads.utils_time import update_datetime_source
from mat.gps_quectel import gps_configure_quectel
from mat.utils import linux_is_rpi


def _boot_sync_time(w):
    """ th_boot gets datetime source """

    update_datetime_source(w)


def _boot_sync_position(w):
    """ th_boot gets first GPS position """

    _o = utils_gps_get_one_lat_lon_dt()
    w.sig_gps.update.emit(_o)


def _boot_connect_gps(w):
    # tries twice to enable GPS, used for position and time source
    if linux_is_rpi() and not dbg_hook_make_gps_give_fake_measurement:
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
    _boot_connect_gps(w)
    _boot_sync_time(w)
    _boot_sync_position(w)

    # now, allow other threads to boot
    w.sig_boot.status.emit('SYS: th_boot starting other threads')
    evb.set()


