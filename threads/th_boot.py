import time
from threads.utils_gps_internal import gps_get_one_lat_lon_dt
from threads.utils_time import time_via


def _boot_sync_time(w):
    time_via(w)


def _boot_sync_position(w):
    _o = gps_get_one_lat_lon_dt()
    w.sig_gps.update.emit(_o)


def boot(w, evb):
    # give time GUI to finish booting
    time.sleep(.5)
    _boot_sync_time(w)
    _boot_sync_position(w)
    w.sig_boot.status.emit('SYS: th_boot starting other threads')
    evb.set()


