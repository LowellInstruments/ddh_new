import sys
import subprocess as sp
from mat.utils import PrintColors as PC
from tools.recipe_script_utils import (
    frm_n_run,
    get_ordered_scan_results,
)


# include macs for this script, these are different from DDH GUI ones
from tools.recipe_script_macs import dict_mac_to_sn


def _screen_clear(): sp.run('clear', shell=True)
def _screen_separation() : print('\n\n')
def _menu_get(): return input('\t-> ')
def _menu_banner(): print('scan done! nearer loggers listed first')


def _menu_build(_sr: dict, n: int):
    """ builds a menu of up to 'n' entries """

    # sr: scan results, entry: (<mac>, <rssi>)
    d = {}
    for i, each_sr in enumerate(_sr):
        if i == n:
            break
        mac, rssi = each_sr
        sn = dict_mac_to_sn.get(mac, 'SN_not_assigned')
        d[i] = (mac, sn, rssi)
        # menu dict entries are d[number]: (mac, sn, rssi)
    return d


def _menu_show(d: dict):
    print('\nnow, choose an option:')
    print('\ts) search for loggers again')
    print('\tq) quit')
    for k, v in d.items():
        s = '\t{}) deploy {} {} {}'
        print(s.format(k, v[0], v[1], v[2]))


def _menu_do(_m, _c):
    """ deploys the logger chosen from the list """

    # options for leaving and re-searching loggers
    if _c == 'q':
        print('bye!')
        sys.exit(0)
    if _c == 's':
        return

    # safety check, menu keys are integers
    if not str(_c).isnumeric():
        print(PC.WARNING + '\tunknown option' + PC.ENDC)
        return
    _c = int(_c)
    if _c >= len(_m):
        print(PC.WARNING + '\tbad option' + PC.ENDC)
        return

    # do a logger
    mac, sn = _m[_c][0], _m[_c][1]
    assert len(sn) == 7, 'logger serial numbers must be 7 characters long'
    print('\tdeploying logger {}...'.format(mac))
    rv = frm_n_run(mac, sn)
    s_ok = PC.OKGREEN + '\tsuccess {}' + PC.ENDC
    s_nok = PC.FAIL + '\terror {}' + PC.ENDC
    s = s_ok if rv == 0 else s_nok
    print(s.format(mac))


def _loop():
    sr, _ = get_ordered_scan_results(dummies=False)
    _menu_banner()
    m = _menu_build(sr, 10)
    _menu_show(m)
    c = _menu_get()
    _menu_do(m, c)
    _screen_separation()


if __name__ == '__main__':
    _screen_clear()
    while True:
        _loop()
