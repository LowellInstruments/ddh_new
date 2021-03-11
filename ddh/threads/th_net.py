import time
from ddh.threads.utils import wait_boot_signal
from ddh.threads.utils_net import net_check_connectivity, net_get_my_current_wlan_ssid
from ddh.settings import ctx
from mat.utils import linux_is_rpi


TH_NET_PERIOD_S = 60
assert TH_NET_PERIOD_S >= 30


def loop(w, ev_can_i_boot):
    wait_boot_signal(w, ev_can_i_boot, 'NET')

    while 1:
        s = '{}'.format(net_get_my_current_wlan_ssid())
        w.sig_net.update.emit(s)

        if not linux_is_rpi():
            # on a desktop computer, we end here
            time.sleep(TH_NET_PERIOD_S)
            continue

        ctx.sem_ble.acquire()
        ctx.sem_aws.acquire()
        net_check_connectivity(w.sig_net)
        ctx.sem_aws.release()
        ctx.sem_ble.release()
        time.sleep(TH_NET_PERIOD_S)
