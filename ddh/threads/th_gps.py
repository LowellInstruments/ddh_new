import time
from ddh.settings import ctx
from ddh.threads.utils import wait_boot_signal
from ddh.threads.utils_gps_quectel import utils_gps_get_one_lat_lon_dt


PERIOD_GPS = 10


def loop(w, ev_can_i_boot):

    wait_boot_signal(w, ev_can_i_boot, 'GPS')

    # extra delay in booting order since GPS blocks
    time.sleep(1)

    while 1:
        # updates only position, time source updated in other thread
        ctx.sem_ble.acquire()
        _o = utils_gps_get_one_lat_lon_dt()
        w.sig_gps.update.emit(_o)
        ctx.sem_ble.release()
        time.sleep(PERIOD_GPS)
