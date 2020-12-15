import time
from settings import ctx
from threads.utils import wait_boot_signal
from threads.utils_gps_internal import get_gps_lat_lon_more


PERIOD_GPS = 5


def loop(w, ev_can_i_boot):
    wait_boot_signal(w, ev_can_i_boot, 'GPS')

    # helps in booting order since GPS blocks
    time.sleep(1)

    while 1:
        ctx.sem_ble.acquire()
        _o = get_gps_lat_lon_more()
        w.sig_gps.update.emit(_o)
        ctx.sem_ble.release()
        time.sleep(PERIOD_GPS)
