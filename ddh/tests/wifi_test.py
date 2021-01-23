import subprocess as sp
from wifi import Cell
import wifi


def _get_known_wifi_names():
    c = 'wpa_cli list_networks'
    s = sp.run(c, shell=True, stdout=sp.PIPE)
    s = s.stdout.decode().rstrip('\n')
    print(s)
    return s


def _get_around_wifi_names(iface: str):
    try:
        wn = []
        around = Cell.all(iface)
        for _ in around:
            if _.ssid != '':
                wn.append(_.ssid)
        return wn
    except wifi.exceptions.InterfaceError:
        print('interface name {} bad?'.format(iface))
        return []


if __name__ == '__main__':
    kn = _get_known_wifi_names()
    an = _get_around_wifi_names('wlan0')

    for _ in an:
        if _ in kn:
            print('some known network around')
