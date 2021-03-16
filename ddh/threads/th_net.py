import time
from ddh.threads.utils import wait_boot_signal
from ddh.threads.utils_net import net_check_connectivity, net_get_my_current_wlan_ssid
from ddh.settings import ctx
from mat.utils import linux_is_rpi


TH_NET_PERIOD_S = 60
assert TH_NET_PERIOD_S >= 30


def loop(w, ev_can_i_boot):
    wait_boot_signal(w, ev_can_i_boot, 'NET')
    is_rpi = linux_is_rpi()

    # on a desktop computer, we stay here
    while 1:
        if is_rpi:
            break
        s = '{}'.format(net_get_my_current_wlan_ssid())
        w.sig_net.update.emit(s)
        time.sleep(TH_NET_PERIOD_S)

    # on a raspberry DDH, we stay here
    while 1:
        ctx.sem_ble.acquire()
        ctx.sem_aws.acquire()
        net_check_connectivity(w.sig_net)
        ctx.sem_aws.release()
        ctx.sem_ble.release()
        time.sleep(TH_NET_PERIOD_S)
