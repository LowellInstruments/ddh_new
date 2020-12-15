import time
from threads.utils_gps_internal import get_gps_data
from threads.utils_time import time_via


def sync_boot_time(w):
    time_via(w)


def sync_boot_position(w):
    _o = get_gps_data()
    w.sig_gps.update.emit(_o)


def boot(w, evb):
    # give time GUI to finish booting
    time.sleep(.5)
    sync_boot_time(w)
    sync_boot_position(w)
    w.sig_boot.status.emit('SYS: th_boot starting other threads')
    evb.set()


