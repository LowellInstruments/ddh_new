import ipaddress
import socket
import subprocess as sp
import time
import wifi
from wifi import Cell, exceptions
from ddh.threads.utils import emit_status, emit_update
from mat.utils import linux_is_rpi


# multiplies sleep (TH_NET_PERIOD_S) in thread code
_NET_MAX_SW_WIFI_COUNTDOWN = 5

# initially set to 1 to not disturb during DDH boot
_net_sw_wifi_countdown = 1
_via_inet_last = ''


def _shell(s):
    rv = sp.run(s, shell=True, stdout=sp.DEVNULL)
    return rv.returncode


def _net_set_via_to_internet_as_cell():
    _shell('sudo ifmetric ppp0 0')


def _net_set_via_to_internet_as_wifi():
    _shell('sudo ifmetric ppp0 400')


def _net_get_my_current_wlan_ssid() -> str:
    c = 'iwgetid -r'
    s = sp.run(c, shell=True, stdout=sp.PIPE)
    return s.stdout.decode().rstrip('\n')


def net_get_my_current_wlan_ssid():
    return _net_get_my_current_wlan_ssid()


def _net_get_known_wlan_ssids():
    try:
        c = 'wpa_cli list_networks'
        s = sp.run(c, shell=True, stdout=sp.PIPE)
        s = s.stdout.decode().rstrip('\n')
        return s
    except OSError:
        return ''


def _net_get_nearby_wlan_ssids(interface: str):
    try:
        wn = []
        around = Cell.all(interface)
        for _ in around:
            if _.ssid != '':
                wn.append(_.ssid)
        return wn
    except wifi.exceptions.InterfaceError:
        e = 'interface {} exists?'.format(interface)
        print(e)
        return None


def _net_is_worth_trying_sw_wifi(interface: str) -> bool:
    if not linux_is_rpi():
        print('no RPI system, no wpa_cli')
        return False

    kn = _net_get_known_wlan_ssids()
    an = _net_get_nearby_wlan_ssids(interface)

    if an is None:
        # interface wi-fi error, sure to try switching
        return True

    for _ in an:
        if _ in kn:
            return True
    return False


def _net_switch_via_to_internet(sig, org=None):
    global _net_sw_wifi_countdown
    assert org in ('none', 'cell')

    # network: none at all, try switching to cell
    if org == 'none':
        emit_status(sig, 'no network, trying none -> cell')
        _net_set_via_to_internet_as_cell()
        # optimistic countdown reload for next loop, maybe will be cell
        _net_sw_wifi_countdown = _NET_MAX_SW_WIFI_COUNTDOWN
        return

    # network: we are cell
    s = '{} steps left to try a switch to wi-fi'
    emit_status(sig, s.format(_net_sw_wifi_countdown))
    if _net_sw_wifi_countdown == 0:
        _net_sw_wifi_countdown = _NET_MAX_SW_WIFI_COUNTDOWN
        if _net_is_worth_trying_sw_wifi('wlan0'):
            emit_status(sig, 'trying cell -> wifi')
            _net_set_via_to_internet_as_wifi()
        else:
            s = 'NET: unworthy trying cell -> wifi'
            emit_status(sig, s)
    if _net_sw_wifi_countdown >= 1:
        _net_sw_wifi_countdown -= 1


def _net_get_my_ip_to_internet():
    """
    returns '169.x' (zeroconf), '192.x / 10.x' (wi-fi),
    '25.x' (cell) or None
    """

    try:
        sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except (OSError, Exception) as ex:
        print('SYS: ' + str(ex))
        return

    adr = ('8.8.8.8', 80)
    try:
        sk.connect(adr)
        rv = sk.getsockname()[0]
    except OSError as oe:
        print('OSerror {}'.format(oe))
        rv = None

    if sk.connect_ex(adr):
        sk.shutdown(socket.SHUT_RDWR)
        sk.close()

    return rv


def _net_get_via_to_internet() -> str:
    """ returns 'wifi', 'cell' or 'none' """

    ip = _net_get_my_ip_to_internet()

    # when zero-conf address, ensure interface is up
    if ip and ip.startswith('169.'):
        _shell('sudo ifconfig wlan0 down')
        _shell('sudo ifconfig wlan0 up')
        time.sleep(5)

    # no internet, or zero-conf address
    if not ip:
        return 'none'
    if ip.startswith('0.0.0.0'):
        return 'none'
    if ip.startswith('169.'):
        return 'none'

    # some valid internet IP address
    _ = ipaddress.ip_address(ip)
    return 'wifi' if _.is_private else 'cell'


def net_check_connectivity(sig=None):
    """
    preferred: wi-fi > cell > no net
    check: RFKill on wi-fi
    """

    global _net_sw_wifi_countdown
    global _via_inet_last
    via_inet_now = _net_get_via_to_internet()

    # conditional update :)
    if via_inet_now != _via_inet_last:
        if via_inet_now == 'wifi':
            ssid = _net_get_my_current_wlan_ssid()
            emit_update(sig, 'NET: wifi {}'.format(ssid))
        else:
            # 'cell' or 'none'
            emit_update(sig, 'NET: {}'.format(via_inet_now))
    _via_inet_last = via_inet_now

    if via_inet_now == 'wifi':
        _net_sw_wifi_countdown = _NET_MAX_SW_WIFI_COUNTDOWN
        return

    # in case via is 'cell' or 'none'
    _net_switch_via_to_internet(sig, org=via_inet_now)


if __name__ == '__main__':
    while 1:
        net_check_connectivity()
        time.sleep(5)
