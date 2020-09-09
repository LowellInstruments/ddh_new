import time
from random import random
from context import ctx
from threads.utils_ftp import ftp_sync, emit_status, emit_conn


class ThFTP:
    PERIOD_FTP = 300
    assert (PERIOD_FTP >= 30)

    def __init__(self, sig):
        self.sig = sig
        emit_status(self.sig, 'FTP: thread boot')

        # prevent threads starting same time
        time.sleep(random())

        while 1:
            if not ctx.ftp_en:
                emit_conn(sig, 'FTP: disabled')
                time.sleep(5)
                continue

            if ctx.ble_ongoing:
                # emit_status(sig, 'FTP: wait BLE to finish')
                time.sleep(5)
                continue

            ctx.ftp_ongoing = True
            ftp_sync(sig)
            ctx.ftp_ongoing = False
            p = self.PERIOD_FTP + (10 * random())
            time.sleep(p)


def fxn(sig):
    ThFTP(sig)
