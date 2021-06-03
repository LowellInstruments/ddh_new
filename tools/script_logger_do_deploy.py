import sys
import subprocess as sp
from mat.utils import PrintColors as PC
from _script_logger_do_deploy_utils import (
    frm_n_run,
    get_ordered_scan_results, get_script_cfg_file, set_script_cfg_file_do_value,
)
import yaml
import os


def _screen_clear(): sp.run('clear', shell=True)
def _check_cwd(): assert os.getcwd().endswith('tools')
def _screen_separation() : print('\n\n')
def _menu_get(): return input('\t-> ')


# indicates  RUN command is issued at end of logger configuration
g_flag_run = False


def _menu_build(_sr: dict, n: int):
    """
    builds a menu of up to 'n' entries
    only entries in '_macs_to_sn.yml' files are valid
    """

    # get entries in DDH folder mac-to-sn YAML file, if any
    ddh_d = {}
    try:
        # note: at PyCharm edit 'run configuration' working directory
        with open('../ddh/settings/_macs_to_sn.yml') as f:
            ddh_d = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError:
        pass

    # warning
    if not ddh_d:
        e = 'DDH _macs_to_sn.yml file found'
        print(PC.FAIL + e + PC.ENDC)
        return

    # ensure lower-case for all entries
    ddh_d = dict((k.lower(), v) for k, v in ddh_d.items())

    # sr: scan results, entry: (<mac>, <rssi>)
    d = {}
    for i, each_sr in enumerate(_sr):
        if i == n:
            break

        mac, rssi = each_sr

        # filter by known mac in files
        if mac not in ddh_d:
            continue

        # menu dict entries are d[number]: (mac, sn, rssi)
        sn = str(ddh_d[mac])
        d[i] = (mac, sn, rssi)

    return d


def _menu_show(d: dict, cfg: dict):
    global g_flag_run
    do_i = cfg['DRI']
    print('scan done! nearer loggers listed first')
    print('\nnow, choose an option:')
    print('\ts) scan for valid loggers again')
    print('\tr) toggle RUN flag, current value is {}'.format(g_flag_run))
    print('\ti) set DO interval, current value is {}'.format(do_i))
    print('\tq) quit')
    if not d:
        return
    for k, v in d.items():
        s = '\t{}) deploy {} {} {}'
        print(s.format(k, v[0], v[1], v[2]))


def _menu_do(_m, _c, cfg):
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
    if _c == 'i':
        # set new DO interval
        try:
            i = int(input('\t\t enter new interval -> '))
        except ValueError:
            print('invalid input: must be number')
            return
        valid = (30, 60, 300, 600, 900, 3600, 7200)
        if i not in valid:
            print('invalid interval: must be {}'.format(valid))
            return
        cfg['DRI'] = i
        set_script_cfg_file_do_value(cfg)
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
    cfg = get_script_cfg_file()
    sr, _ = get_ordered_scan_results()
    m = _menu_build(sr, 10)
    _menu_show(m, cfg)
    c = _menu_get()
    _menu_do(m, c, cfg)
    _screen_separation()


if __name__ == '__main__':
    _screen_clear()
    _check_cwd()
    while True:
        _loop()
