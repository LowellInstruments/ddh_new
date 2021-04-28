import json

import time
import bluepy.btle as ble
from bluepy.btle import Scanner
from mat.logger_controller_ble import FAKE_MAC_CC26X2, LED_CMD, WAKE_CMD, SLOW_DWL_CMD
from mat.logger_controller import (LOGGER_INFO_CMD_W,
                                   LOGGER_INFO_CMD,
                                   STOP_CMD,
                                   STATUS_CMD,
                                   RUN_CMD,
                                   DO_SENSOR_READINGS_CMD, RWS_CMD)
from mat.logger_controller_ble_factory import LcBLEFactory


def _ensure_wake_mode_is_on(lc):
    """ query and ensure logger WAK flag is 1 """

    rv = lc.command(WAKE_CMD)
    if rv == b'ERR':
        return rv

    wak_is_on = rv[1].decode()[-1]
    if wak_is_on == '1':
        return 'ON'

    rv = lc.command(WAKE_CMD)
    if rv == b'ERR':
        return rv

    wak_is_on = rv[1].decode()[-1]
    if wak_is_on == '1':
        return 'ON'

    return 'OFF'


def _ensure_slow_dwl_mode_is_on(lc):
    """ query and ensure logger SLOW_DWL_CMD flag is 1 """

    rv = lc.command(SLOW_DWL_CMD)
    if rv == b'ERR':
        return rv

    slow_dwl_mode_is_on = rv[1].decode()[-1]
    if slow_dwl_mode_is_on == '1':
        return 'ON'

    rv = lc.command(SLOW_DWL_CMD)
    if rv == b'ERR':
        return rv

    slow_dwl_mode_is_on = rv[1].decode()[-1]
    if slow_dwl_mode_is_on == '1':
        return 'ON'

    return 'OFF'


def get_script_cfg_file():
    # let it crash on purpose, if so
    with open('./script_logger_do_deploy_cfg.json') as f:
        return json.load(f)


def set_script_cfg_file_do_value(cfg_d: dict):
    with open('./script_logger_do_deploy_cfg.json', 'w') as f:
        return json.dump(cfg_d, f)


# resets a logger memory and runs it
def frm_n_run(mac, sn, flag_run):
    try:
        lc = LcBLEFactory.generate(mac)
        ok = 0
        with lc(mac) as lc:
            # sets up logger time, memory, serial number, tests leds
            rv = lc.command(STATUS_CMD)
            print('\t\tSTS --> {}'.format(rv))
            ok += b'ERR' in rv

            rv = lc.command(LED_CMD)
            print('\t\tLED --> {}'.format(rv))
            ok += b'ERR' in rv

            rv = lc.command(STOP_CMD)
            print('\t\tSTP --> {}'.format(rv))
            ok += b'ERR' in rv

            rv = lc.sync_time()
            print('\t\tSTM --> {}'.format(rv))
            ok += b'ERR' in rv

            rv = lc.get_time()
            print('\t\tGTM --> {}'.format(rv))
            ok += not rv

            rv = lc.command('FRM')
            print('\t\tFRM --> {}'.format(rv))
            ok += b'ERR' in rv

            cfg_file = get_script_cfg_file()
            print(cfg_file)
            rv = lc.send_cfg(cfg_file)
            print('\t\tCFG --> {}'.format(rv))
            ok += b'ERR' in rv

            rv = lc.command(LOGGER_INFO_CMD_W, 'BA8007')
            print('\t\tWLI (BA) --> {}'.format(rv))
            ok += b'ERR' in rv

            rv = lc.command(LOGGER_INFO_CMD, 'BA')
            print('\t\tRLI (BA) --> {}'.format(rv))
            ok += b'ERR' in rv

            s = 'SN{}'.format(sn)
            rv = lc.command(LOGGER_INFO_CMD_W, s)
            print('\t\tWLI (SN) --> {}'.format(rv))
            ok += b'ERR' in rv

            rv = lc.command(LOGGER_INFO_CMD, 'SN')
            print('\t\tRLI (SN) --> {}'.format(rv))
            ok += b'ERR' in rv

            rv = _ensure_wake_mode_is_on(lc)
            print('\t\tWAK --> {}'.format(rv))
            ok += rv in [b'ERR', 'OFF']

            rv = _ensure_slow_dwl_mode_is_on(lc)
            print('\t\tSLW --> {}'.format(rv))
            ok += rv in [b'ERR', 'OFF']

            rv = lc.command(DO_SENSOR_READINGS_CMD)
            print('\t\tGDO --> {}'.format(rv))
            ok += b'ERR' in rv

            # starts the logger, depending on flag
            if flag_run:
                time.sleep(1)
                rv = lc.command(RWS_CMD, 'LAB LAB')
                print('\t\tRWS / RUN --> {}'.format(rv))
                ok += b'ERR' in rv
            else:
                print('\t\tRWS / RUN --> omitted: current flag value is False')

            # ok != 0 is bad
            return ok

    except ble.BTLEException as ex:
        print('BLE: connect exception --> {}'.format(ex))


def get_ordered_scan_results() -> tuple:
    """
    Performs a BLE scan and returns two dictionaries
    :return: near and far lists
    """

    till = 3
    s = 'detecting nearby loggers, please wait {} seconds...'
    print(s.format(till))
    sr = Scanner().scan(float(till))

    # bluepy 'scan results (sr)' format -> friendlier one
    sr_f = {each_sr.addr: (each_sr.rssi, each_sr.rawData) for each_sr in sr}

    # filter: only keep lowell instruments' DO-1 loggers
    sr_f = {k: v[0] for k, v in sr_f.items() if v[1] and b'DO-1' in v[1]}

    # nearest: the highest value, less negative
    sr_f_near = sorted(sr_f.items(), key=lambda x: x[1], reverse=True)
    sr_f_far = sorted(sr_f.items(), key=lambda x: x[1], reverse=False)
    return sr_f_near, sr_f_far
