import os
import sys
import time

from ddh.settings import ctx
from ddh.settings.ctx import dbg_hook_make_gps_give_fake_measurement
from ddh.threads.utils_gps_quectel import utils_gps_get_one_lat_lon_dt, utils_gps_cache_clear
from ddh.threads.utils_time import utils_time_update_datetime_source
from mat.gps_quectel import gps_configure_quectel
from mat.utils import linux_is_rpi


# Wikipedia: GPS-Time-To-First-Fix for cold start is typ.
# 2 to 4 minutes, warm <= 45 secs, hot <= 22 secs
BOOT_GPS_1ST_FIX_TIMEOUT = 240
BOOT_GPS_WAIT_MESSAGE = 'wait {} minutes on GPS cold start'


def _boot_sync_time(w):
    """ th_boot gets datetime source """

    rv = 'local'
    desktop_or_no_cell_shield = (not linux_is_rpi()) or (not ctx.cell_shield_en)
    list_src = ('NTP', ) if not desktop_or_no_cell_shield else ('GPS', 'NTP')
    for i in range(3):
        rv = utils_time_update_datetime_source(w)
        if rv in list_src:
            break
        time.sleep(5)
    w.sig_boot.debug.emit('BOO: sync time {}'.format(rv))


def _boot_sync_position(w):
    """ th_boot gets first GPS position """

    desktop_or_no_cell_shield = (not linux_is_rpi()) or (not ctx.cell_shield_en)
    if desktop_or_no_cell_shield:
        e = 'no GPS / cell shield to wait position'
        w.lbl_ble.setText(e)
        w.sig_boot.debug.emit('BOO: {}'.format(e))
        return

    t = BOOT_GPS_1ST_FIX_TIMEOUT
    w.lbl_ble.setText(BOOT_GPS_WAIT_MESSAGE.format(t / 60))
    _o = utils_gps_get_one_lat_lon_dt(timeout=t, sig=w.sig_gps)
    w.sig_gps.update.emit(_o)


def _boot_connect_gps(w):

    # on Desktop, do not wait
    desktop_or_no_cell_shield = (not linux_is_rpi()) or (not ctx.cell_shield_en)
    if desktop_or_no_cell_shield:
        e = 'no GPS / cell shield to connect to'
        w.lbl_ble.setText(e)
        w.sig_boot.debug.emit('BOO: {}'.format(e))
        return

    # tries twice to enable GPS, used for position and time source
    if not dbg_hook_make_gps_give_fake_measurement:
        rv = gps_configure_quectel()
        if rv == 0:
            return
        time.sleep(1)
        rv = gps_configure_quectel()
        if rv:
            w.sig_boot.error.emit('BOO: error opening GPS port')
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
