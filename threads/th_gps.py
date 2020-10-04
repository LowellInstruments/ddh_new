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

        # wait until first attempt of boot time
        while ctx.boot_time:
            if ctx.boot_time:
                break

        # decouple both time & pos syncs
        steps = 0
        while 1:
            # do not interrupt BLE
            ctx.sem_ble.acquire()
            ctx.sem_ble.release()

            # position more often
            sync_pos(sig)
            if (steps % 10) == 0:
                sync_time(sig)
                steps += 1
            time.sleep(self.PERIOD_GPS)


def fxn(sig):
    ThGPS(sig)
