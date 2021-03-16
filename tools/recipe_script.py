import sys
import subprocess as sp
from mat.utils import PrintColors as PC
from tools.recipe_script_utils import frm_n_run, get_ordered_scan_results


def _screen_clear():
    sp.run('clear', shell=True)


def _menu_build(_sr: dict):
    # sr: scan results5
    d = dict((i, j) for i, j in enumerate(_sr))
    # dict entries> (int, object)
    return d


def _menu_banner():
    s = 'scan done! nearer loggers are listed first'
    print(s)


def _menu_show(d: dict):
    print('\nnow, choose an option:')
    print('\ts) search for loggers again')
    print('\tq) quit')
    for k, v in d.items():
        s = '\t{}) deploy {}'.format(k, v)
        print(s)


def _menu_get():
    s = '\t-> '
    return input(s)


def _menu_do(_m, _c):
    if _c == 'q':
        print('bye!')
        sys.exit(0)
    if _c == 's':
        # asked for a re-scan, just leave
        return

    # safety check, dict keys are integers
    if not str(_c).isnumeric():
        print(PC.WARNING + '\tunknown option' + PC.ENDC)
        return -1
    _c = int(_c)
    if _c >= len(_m):
        print(PC.WARNING + '\tbad option' + PC.ENDC)
        return -1

    # do a logger
    mac = _m[_c][0]
    print('\tdeploying logger {}...'.format(mac))
    rv = frm_n_run(mac, '1234567')
    s_ok = PC.OKGREEN + '\tsuccess {}' + PC.ENDC
    s_nok = PC.FAIL + '\terror {}' + PC.ENDC
    s = s_ok if rv == 0 else s_nok
    print(s.format(mac))


def main_loop():
    _screen_clear()
    sr, _ = get_ordered_scan_results(dummies=True)
    _menu_banner()
    m = _menu_build(sr)
    _menu_show(m)
    c = _menu_get()
    _menu_do(m, c)


if __name__ == '__main__':
    while True:
        main_loop()