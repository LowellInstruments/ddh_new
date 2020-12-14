import threading
import time
from settings import ctx
from threads.utils_gps_internal import get_gps_lat_lon_more


PERIOD_GPS = 5


def loop(w):
    # w: Qt5 windowed app
    def _th():
        _o = get_gps_lat_lon_more()
        w.sig_gps.update.emit(_o)

    # throw thread
    while 1:
        ctx.sem_ble.acquire()
        ctx.sem_ble.release()
        th = threading.Thread(target=_th)
        th.start()
        th.join()
        time.sleep(PERIOD_GPS)
