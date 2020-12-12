import time
from mat.linux import linux_is_rpi
from threads.utils_net import check_net_best, emit_net_status, ensure_resolv_conf, get_ssid, emit_net_update
from settings import ctx


TH_NET_PERIOD = 60


def loop(w):
    assert TH_NET_PERIOD >= 30

    while 1:
        if not linux_is_rpi():
            s = '{}'.format(get_ssid())
            w.sig_net.update.emit(s)
            time.sleep(60)
            continue

        ctx.sem_ble.acquire()
        ctx.sem_ble.release()
        ctx.sem_ftp.acquire()
        ensure_resolv_conf()
        check_net_best(w.sig_net)
        ctx.sem_ftp.release()
        time.sleep(TH_NET_PERIOD)
