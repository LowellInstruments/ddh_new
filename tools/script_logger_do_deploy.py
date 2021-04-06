import sys
import subprocess as sp
from mat.utils import PrintColors as PC
from script_logger_do_deploy_utils import (
    frm_n_run,
    get_ordered_scan_results,
)
import yaml
import os


def _screen_clear(): sp.run('clear', shell=True)
def _check_cwd(): assert os.getcwd().endswith('tools')
def _screen_separation() : print('\n\n')
def _menu_get(): return input('\t-> ')
def _menu_banner(): print('scan done! nearer loggers listed first')


# indicates  RUN command is issued at end of logger configuration
g_flag_run = False


def _menu_build(_sr: dict, n: int):
    """
    builds a menu of up to 'n' entries
    only entries in '_macs_to_sn.yml' files are valid
    """

    # get entries in current folder's mac-to-sn YAML file, if any
    l_d = {}
    try:
        with open('./_macs_to_sn.yml') as f:
            l_d = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError:
        pass

    # get entries in DDH folder mac-to-sn YAML file, if any
    ddh_d = {}
    try:
        # note: at PyCharm edit 'run configuration' working directory
        with open('../ddh/settings/_macs_to_sn.yml') as f:
            ddh_d = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError:
        pass

    # warning
    if not ddh_d and not l_d:
        e = 'no local or DDH _macs_to_sn.yml file found'
        print(PC.FAIL + e + PC.ENDC)
        return

    # ensure lower-case for all entries
    l_d = dict((k.lower(), v) for k, v in l_d.items())
    ddh_d = dict((k.lower(), v) for k, v in ddh_d.items())

    # sr: scan results, entry: (<mac>, <rssi>)
    d = {}
    for i, each_sr in enumerate(_sr):
        if i == n:
            break

        mac, rssi = each_sr

        # filter by known mac in files
        if mac not in l_d and mac not in ddh_d:
            continue

        # info from local file has precedence
        try:
            sn = str(l_d[mac])
        except KeyError:
            sn = str(ddh_d[mac])

        d[i] = (mac, sn, rssi)
        # menu dict entries are d[number]: (mac, sn, rssi)
    return d


def _menu_show(d: dict):
    global g_flag_run
    print('\nnow, choose an option:')
    print('\ts) scan for valid loggers again')
    print('\tr) toggle RUN flag, current value is {}'.format(g_flag_run))
    print('\tq) quit')
    if not d:
        return
    for k, v in d.items():
        s = '\t{}) deploy {} {} {}'
        print(s.format(k, v[0], v[1], v[2]))


def _menu_do(_m, _c):
    """ deploys the logger chosen from the list """
    global g_flag_run

    # _c: user choice
    if _c == 'q':
        # quit
        print('bye!')
        sys.exit(0)
    if _c == 's':
        # re-scan BLE loggers around
        return
    if _c == 'r':
        # toggle run flag
        g_flag_run = not g_flag_run
        return

    # safety check, menu keys are integers
    if not str(_c).isnumeric():
        print(PC.WARNING + '\tunknown option' + PC.ENDC)
        return
    _c = int(_c)
    if _c >= len(_m):
        print(PC.WARNING + '\tbad option' + PC.ENDC)
        return

    # _m: built menu w/ macs & sn, let's do a logger
    mac, sn = _m[_c][0], _m[_c][1]
    if len(sn) != 7:
        e = '\terror: got {}, but serial numbers must be 7 digits long'
        print(PC.FAIL + e.format(sn) + PC.ENDC)
        return

    print('\tdeploying logger {}...'.format(mac))
    rv = frm_n_run(mac, sn, g_flag_run)
    s_ok = PC.OKGREEN + '\tsuccess {}' + PC.ENDC
    s_nok = PC.FAIL + '\terror {}' + PC.ENDC
    s = s_ok if rv == 0 else s_nok
    print(s.format(mac))


def _loop():
    sr, _ = get_ordered_scan_results()
    _menu_banner()
    m = _menu_build(sr, 10)
    _menu_show(m)
    c = _menu_get()
    _menu_do(m, c)
    _screen_separation()


if __name__ == '__main__':
    _screen_clear()
    _check_cwd()
    while True:
        _loop()
