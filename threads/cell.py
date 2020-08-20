import ipaddress
import socket
import subprocess as sp
import time
from logzero import logger as console_log


sw_steps = 0


def emit_net_status(sig, s):
    if sig:
        sig.net_status.emit(s)


def _emit_net_rv(sig, i):
    if sig:
        sig.net_rv.emit(i)


def __restore_resolv_conf():
    # resolv.conf may get written, restore it
    s = 'sudo bash -c \'echo '
    s += '"nameserver 8.8.8.8" > /etc/resolv.conf\''
    __shell(s)


def __shell(s):
    rv = sp.run(s, shell=True, stdout=sp.DEVNULL)
    return rv.returncode


def __switch_net_to_cell():
    __shell('sudo ip route del default')
    __shell('sudo ip route add default dev ppp0')


def __switch_net_to_wifi():
    __shell('sudo ip route del default')
    __shell('sudo ip route add default dev wlan0')


def _switch_net(sig, org=None):
    assert org in ('none', 'cell')
    if org == 'none':
        __switch_net_to_cell()
    elif org == 'cell':
        global sw_steps
        if not sw_steps:
            print('trying sw from cell')
            __switch_net_to_wifi()
            sw_steps = 5
        sw_steps -= 1
    __restore_resolv_conf()


def __get_ip():
    # cell (172.x) zeroconf (169.x) wi-fi (ISP)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None


def _get_net_type() -> str:
    ip_s = __get_ip()

    # no internet or zero-conf address
    if not ip_s:
        return 'none'
    if ip_s.startswith('0.0.0.0'):
        return 'none'
    if ip_s.startswith('169.'):
        return 'none'

    # some internet connection
    my_ip = ipaddress.ip_address(ip_s)
    if my_ip.is_private:
        return 'wifi'
    return 'cell'


def check_net_best(sig=None):
    # preferred: wi-fi > cell > no net
    nt = _get_net_type()
    print('nt {}'.format(nt))
    if nt == 'wifi':
        c = 'iwgetid -r'
        s = sp.run(c, shell=True, stdout=sp.PIPE)
        s = s.stdout.decode().rstrip('\n')
        t = 'NET: wi-fi \n{}'.format(s)
        _emit_net_rv(sig, t)
    else:
        _switch_net(sig, org=nt)
        t = 'NET: {}'.format(nt)
        _emit_net_rv(sig, t)


if __name__ == '__main__':
    __restore_resolv_conf()
    while 1:
        check_net_best()
        time.sleep(5)

