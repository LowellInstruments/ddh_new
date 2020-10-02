import time
from mat.linux import linux_is_rpi
from threads.utils_net import check_net_best, emit_net_status, ensure_resolv_conf, get_ssid, emit_net_update
from settings import ctx


TH_NET_PERIOD = 60


class ThNET:
    assert TH_NET_PERIOD >= 30

    def __init__(self, sig):
        emit_net_status(sig, 'NET: thread boot')
        ensure_resolv_conf()

        while 1:
            if not linux_is_rpi():
                _ = '{}'.format(get_ssid())
                emit_net_update(sig, _)
                time.sleep(60)
                continue

            if not ctx.boot_time:
                emit_net_status(sig, 'NET: wait GPS boot time')
                time.sleep(10)
                continue

            if ctx.ftp_ongoing:
                emit_net_status(sig, 'NET: wait FTP to finish')
                time.sleep(10)
                continue

            if ctx.ble_ongoing:
                emit_net_status(sig, 'NET: wait BLE to finish')
                time.sleep(10)
                continue

            check_net_best(sig)
            time.sleep(TH_NET_PERIOD)


def fxn(sig):
    ThNET(sig)
