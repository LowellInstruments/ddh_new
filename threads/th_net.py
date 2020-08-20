import time
from random import random

from threads.utils import linux_rpi
from threads.utils_net import check_net_best, emit_net_status
from context import ctx


TH_NET_PERIOD = 10
assert TH_NET_PERIOD >= 10


class ThNET:
    def __init__(self, sig):
        self.sig = sig
        emit_net_status(self.sig, 'NET: thread boot')

        while 1:
            # if not linux_rpi():
            #     emit_net_status(sig, 'NET: not a RPi system')
            #     time.sleep(5)
            #     continue

            if ctx.ftp_ongoing:
                emit_net_status(sig, 'NET: wait FTP to finish')
                time.sleep(5)
                continue

            if ctx.ble_ongoing:
                # emit_net_status(sig, 'NET: wait BLE to finish')
                time.sleep(5)
                continue

            check_net_best(self.sig)
            time.sleep(TH_NET_PERIOD + random())


def fxn(sig):
    ThNET(sig)
