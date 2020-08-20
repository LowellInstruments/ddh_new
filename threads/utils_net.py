import ipaddress
import socket
import subprocess as sp
import time

from threads.utils_wifi import worth_trying_sw_wifi

SW_STEPS_RELOAD = 10
sw_steps = 0


def emit_net_status(sig, s):
    if sig:
        sig.net_status.emit(s)
    else:
        print(s)


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
    __shell('sudo ifmetric ppp0 0')


def __switch_net_to_wifi():
    __shell('sudo ifmetric ppp0 400')


def _switch_net(sig, org=None):
    global sw_steps
    assert org in ('none', 'cell')
    if org == 'none':
        sw_steps = SW_STEPS_RELOAD
        __switch_net_to_cell()
    elif org == 'cell':
        q = sw_steps
        s = 'try cell -> wifi count-down {}'
        s = s.format(q)
        emit_net_status(sig, s)
        if not sw_steps:
            rv = worth_trying_sw_wifi('wlan0')
            y = 'YES' if rv else 'NOT'
            s = '{} worth trying cell -> wifi'.format(y)
            emit_net_status(sig, s)
            if rv:
                __switch_net_to_wifi()
        if sw_steps >= 1:
            sw_steps -= 1
    __restore_resolv_conf()


def __get_ip():
    # zeroconf (169.x)
    # wi-fi (192.x / 10.x)
    # cell (25.x)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None


def _get_net_type() -> str:
    ip_s = __get_ip()

    # when zero-conf address, try again
    if ip_s.startswith('169.'):
        __shell('sudo ifconfig wlan0 down')
        __shell('sudo ifconfig wlan0 up')
        time.sleep(5)

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
        # only via wifi we reset cell counters
        global sw_steps
        sw_steps = SW_STEPS_RELOAD
        return 'wifi'
    return 'cell'


def check_net_best(sig=None):
    # preferred: wi-fi > cell > no net
    nt = _get_net_type()
    # print('nt {}'.format(nt))
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
