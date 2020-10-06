import time
from settings import ctx
from threads.utils_gps import (
    sync_pos,
    sync_time, check_gps_hw)
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
        gps_hw_ok = True
        while 1:
            # do not interrupt BLE
            ctx.sem_ble.acquire()
            ctx.sem_ble.release()

            # check GPS hardware, less often
            if not gps_hw_ok or (steps % 10) == 0:
                gps_hw_ok = check_gps_hw(sig)

            # don't do the rest of stuff if no hardware
            if not gps_hw_ok:
                time.sleep(100)
                continue

            # sync time, less often
            if (steps % 10) == 0:
                sync_time(sig)
                steps += 1

            # sync position, more often
            sync_pos(sig)

            time.sleep(self.PERIOD_GPS)


def fxn(sig):
    ThGPS(sig)
