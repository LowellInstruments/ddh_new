import time
from ddh.threads.utils import wait_boot_signal
from ddh.threads.utils_net import net_check_connectivity, net_get_my_current_wlan_ssid
from ddh.settings import ctx
from mat.utils import linux_is_rpi


TH_NET_PERIOD_S = 60
assert TH_NET_PERIOD_S >= 30


def loop(w, ev_can_i_boot):
    """
    checks we have the best network connection possible
    """

    # maybe no need for th_net to be blocked
    # wait_boot_signal(w, ev_can_i_boot, 'NET')

    # check our platform CELL capabilities
    desktop_or_no_cell_shield = (not linux_is_rpi()) or (not ctx.cell_shield_en)
    cell_present = not desktop_or_no_cell_shield
    w.sig_net.status.emit('NET: cell features -> {}'.format(cell_present))

    # loop here when desktop computer or DDH w/o cell
    old_s = ''
    while desktop_or_no_cell_shield:
        s = net_get_my_current_wlan_ssid()
        if s != old_s:
            w.sig_net.update.emit('no network' if not s else s)
        old_s = s
        time.sleep(TH_NET_PERIOD_S)

    # loop here when DDH w/ cell shield
    while 1:
        ctx.sem_ble.acquire()
        ctx.sem_aws.acquire()
        net_check_connectivity(w.sig_net)
        ctx.sem_aws.release()
        ctx.sem_ble.release()
        time.sleep(TH_NET_PERIOD_S)
