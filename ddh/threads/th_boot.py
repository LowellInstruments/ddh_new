import time
from ddh.threads.utils_gps_internal import gps_get_one_lat_lon_dt
from ddh.threads.utils_time import update_datetime_source
from mat.gps_quectel import configure_gps_internal


def _boot_sync_time(w):
    """ th_boot gets datetime source """
    update_datetime_source(w)


def _boot_sync_position(w):
    """ th_boot gets first GPS position """
    _o = gps_get_one_lat_lon_dt()
    w.sig_gps.update.emit(_o)


def boot(w, evb):
    """ allows GUI to boot and does pre-threads things """
    time.sleep(.5)

    # tries to enable GPS, used for position and time source
    configure_gps_internal()

    # gets first values for position and time and their sources
    _boot_sync_time(w)
    _boot_sync_position(w)

    # now, allow other threads to boot
    w.sig_boot.status.emit('SYS: th_boot starting other threads')
    evb.set()


