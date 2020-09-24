import time
from settings import ctx
from threads.utils_gps import (
    sync_pos,
    sync_time)
from threads.utils_gps import emit_gps_status


def try_time_sync_boot_before_ble(sig):
    # DDH may use local time if switched on JUST when
    # downloading a logger, this could lead to time gaps
    till = 60
    for i in range(60):
        s = 'boot: time sync try {}/{}'.format(i, till)
        sig.gps_status.emit(s)
        if sync_time(None):
            break
        time.sleep(.1)
    ctx.boot_time = 1


class ThGPS:
    PERIOD_GPS = 30
    assert (PERIOD_GPS >= 30)

    def __init__(self, sig):
        emit_gps_status(sig, 'GPS: thread boot')
        try_time_sync_boot_before_ble(sig)

        # wait for first attempt of boot time
        while 1:
            if ctx.boot_time:
                break

        while 1:
            if ctx.ble_ongoing:
                # emit_status(sig, 'GPS: wait BLE to finish')
                time.sleep(5)
                continue

            sync_pos(sig)
            sync_time(sig)
            time.sleep(self.PERIOD_GPS)


def fxn(sig):
    ThGPS(sig)
