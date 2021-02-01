import ipaddress
import socket
import subprocess as sp
import time

from ddh.threads.utils import emit_status, emit_update
from ddh.threads.utils_wifi import worth_trying_sw_wifi


SW_RELOAD = 10
# set 'countdown_sw_to_wifi' to 1 to not disturb at boot
countdown_sw_to_wifi = 1


def ensure_resolv_conf():
    # file resolv.conf may get written, restore it w/ good one
    s = 'sudo bash -c \'echo '
    s += '"nameserver 8.8.8.8" > /etc/resolv.conf\''
    _shell(s)


def _shell(s):
    rv = sp.run(s, shell=True, stdout=sp.DEVNULL)
    return rv.returncode


def _switch_net_to_cell():
    _shell('sudo ifmetric ppp0 0')


def _switch_net_to_wifi():
    _shell('sudo ifmetric ppp0 400')


def _switch_net(sig, org=None):
    global countdown_sw_to_wifi
    ensure_resolv_conf()

    assert org in ('none', 'cell')
    if org == 'none':
        # no network at all, so try cell w/ full counter
        countdown_sw_to_wifi = SW_RELOAD
        emit_status(sig, 'no network, trying none -> cell')
        _switch_net_to_cell()
        return

    # we are cell
    i = countdown_sw_to_wifi * SW_RELOAD
    # todo: check this print seconds calculation, since it may be wrong
    s = 'countdown_to_switch_to_wifi is {}s'.format(i)
    emit_status(sig, s.format(countdown_sw_to_wifi))
    if countdown_sw_to_wifi == 0:
        if worth_trying_sw_wifi('wlan0'):
            emit_status(sig, 'trying cell -> wifi')
            _switch_net_to_wifi()
        else:
            s = 'NET: unworthy trying cell -> wifi'
            emit_status(sig, s)
    if countdown_sw_to_wifi >= 1:
        countdown_sw_to_wifi -= 1


def _get_ip():
    try:
        sk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except (OSError, Exception) as ex:
        print('SYS: ' + str(ex))
        return

    address = ('8.8.8.8', 80)
    try:
        sk.connect(address)
        # zeroconf (169.), wi-fi (192. / 10.), cell (25.x)
        rv = sk.getsockname()[0]
    except OSError as oe:
        print('OSerror {}'.format(oe))
        rv = None

    if sk.connect_ex(address):
        sk.shutdown(socket.SHUT_RDWR)
        sk.close()

    return rv


def _get_net_type() -> str:
    ip_s = _get_ip()

    # when zero-conf address, ensure interface is up
    if ip_s and ip_s.startswith('169.'):
        _shell('sudo ifconfig wlan0 down')
        _shell('sudo ifconfig wlan0 up')
        time.sleep(5)

    # no internet, or zero-conf address
    if not ip_s:
        return 'none'
    if ip_s.startswith('0.0.0.0'):
        return 'none'
    if ip_s.startswith('169.'):
        return 'none'

    # some internet connection
    my_ip = ipaddress.ip_address(ip_s)
    if my_ip.is_private:
        # wi-fi, so re-set to cell w/ full counter
        global countdown_sw_to_wifi
        countdown_sw_to_wifi = SW_RELOAD
        return 'wifi'
    return 'cell'


def _get_ssid() -> str:
    c = 'iwgetid -r'
    s = sp.run(c, shell=True, stdout=sp.PIPE)
    return s.stdout.decode().rstrip('\n')


def get_ssid():
    return _get_ssid()


def check_net_best(sig=None):
    """
    preferred: wi-fi > cell > no net
    check: RFKill on wi-fi
    """
    nt = _get_net_type()
    if nt == 'wifi':
        ssid = _get_ssid()
        emit_update(sig, '{}'.format(ssid))
        emit_status(sig, 'NET: wi-fi {}'.format(ssid))
        return

    _switch_net(sig, org=nt)
    emit_update(sig, '{}'.format(nt))
    emit_update(sig, 'NET: {}'.format(nt))


if __name__ == '__main__':
    ensure_resolv_conf()
    while 1:
        check_net_best()
        time.sleep(5)
