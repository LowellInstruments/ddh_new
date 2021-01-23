import time
from ddh.threads.utils import wait_boot_signal
from ddh.threads.utils_net import check_net_best, ensure_resolv_conf, get_ssid
from ddh.settings import ctx
from mat.utils import linux_is_rpi

NET_PERIOD = 60


def loop(w, ev_can_i_boot):
    assert NET_PERIOD >= 30
    wait_boot_signal(w, ev_can_i_boot, 'NET')

    while 1:
        if not linux_is_rpi():
            s = '{}'.format(get_ssid())
            w.sig_net.update.emit(s)
            time.sleep(60)
            continue

        ctx.sem_ble.acquire()
        ctx.sem_aws.acquire()
        ensure_resolv_conf()
        check_net_best(w.sig_net)
        ctx.sem_aws.release()
        ctx.sem_ble.release()
        time.sleep(NET_PERIOD)
