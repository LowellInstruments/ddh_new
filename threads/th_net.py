import time
from mat.linux import linux_is_rpi
from threads.utils_net import check_net_best, emit_net_status, ensure_resolv_conf, get_ssid, emit_net_update
from settings import ctx


NET_PERIOD = 60


def loop(w):
    assert NET_PERIOD >= 30
    w.sig_net.status.emit('SYS: NET thread started')

    while 1:
        if not linux_is_rpi():
            s = '{}'.format(get_ssid())
            w.sig_net.update.emit(s)
            time.sleep(60)
            continue

        # don't interrupt BLE
        ctx.sem_ble.acquire()
        ctx.sem_ble.release()

        # protect ongoing AWS transference, if any
        ctx.sem_aws.acquire()
        ensure_resolv_conf()
        check_net_best(w.sig_net)
        ctx.sem_aws.release()
        time.sleep(NET_PERIOD)
