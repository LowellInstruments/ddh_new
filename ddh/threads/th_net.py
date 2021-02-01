import time
from ddh.threads.utils import wait_boot_signal
from ddh.threads.utils_net import net_check_connectivity, net_ensure_my_resolv_conf, net_get_my_wlan_ssid
from ddh.settings import ctx
from mat.utils import linux_is_rpi

NET_PERIOD = 60


def loop(w, ev_can_i_boot):
    assert NET_PERIOD >= 30
    wait_boot_signal(w, ev_can_i_boot, 'NET')

    while 1:
        if not linux_is_rpi():
            s = '{}'.format(net_get_my_wlan_ssid())
            w.sig_net.update.emit(s)
            time.sleep(NET_PERIOD)
            continue

        ctx.sem_ble.acquire()
        ctx.sem_aws.acquire()
        net_ensure_my_resolv_conf()
        net_check_connectivity(w.sig_net)
        ctx.sem_aws.release()
        ctx.sem_ble.release()
        time.sleep(NET_PERIOD)
