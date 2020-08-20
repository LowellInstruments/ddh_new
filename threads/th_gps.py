import time
from random import random
from context import ctx
from threads.utils_gps import (
    sync_pos,
    sync_time)
from threads.utils_gps import emit_status


class ThGPS:
    SS = 10
    assert (SS >= 10)

    def __init__(self, sig):
        self.sig = sig
        emit_status(self.sig, 'GPS: thread boot')

        while 1:
            if ctx.ble_ongoing:
                # emit_status(sig, 'GPS: wait BLE to finish')
                time.sleep(5)
                continue

            sync_pos(sig)
            sync_time(sig)
            time.sleep(self.SS + random())


def fxn(sig):
    ThGPS(sig)
