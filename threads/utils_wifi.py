import subprocess as sp
import time

from wifi import Cell, exceptions
import wifi

from threads.utils import linux_rpi


def _get_known_wifi_names():
    try:
        c = 'wpa_cli list_networks'
        s = sp.run(c, shell=True, stdout=sp.PIPE)
        s = s.stdout.decode().rstrip('\n')
        return s
    except OSError:
        return ''


def _get_around_wifi_names(interface: str):
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


def worth_trying_sw_wifi(interface: str) -> bool:
    if not linux_rpi():
        print('no RPI system, no wpa_supplicant')
        return False

    kn = _get_known_wifi_names()
    an = _get_around_wifi_names(interface)

    if an is None:
        # interface wi-fi error, sure to try switching
        return True

    for _ in an:
        if _ in kn:
            return True
    return False


if __name__ == '__main__':
    while 1:
        time.sleep(1)
        # interface names: wlan0, wlo1...
        if worth_trying_sw_wifi('wlan0'):
            print('some known network around')
