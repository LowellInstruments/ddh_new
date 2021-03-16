import time
import bluepy.btle as ble
from bluepy.btle import Scanner
from mat.logger_controller_ble import FAKE_MAC_CC26X2, LED_CMD
from mat.logger_controller import (LOGGER_INFO_CMD_W,
                                   LOGGER_INFO_CMD,
                                   STOP_CMD,
                                   STATUS_CMD,
                                   RUN_CMD,
                                   DO_SENSOR_READINGS_CMD)
from mat.logger_controller_ble_factory import LcBLEFactory


def get_ordered_scan_results(dummies=False) -> dict:
    """
    Does a BLE scan and returns friendly results lists
    :param dummies: add a couple dummies for resting
    :return: near and far lists
    """

    till = 3
    s = 'detecting nearby loggers, please wait {} seconds...'
    print(s.format(till))
    sr = Scanner().scan(float(till))

    # bluepy 'scan results (sr)' format -> friendlier one
    sr_f = {each_sr.addr: each_sr.rssi for each_sr in sr}

    if dummies:
        sr_f[FAKE_MAC_CC26X2] = -10
        sr_f['dummy_2'] = -20

    # nearest: the highest value, less negative
    sr_f_near = sorted(sr_f.items(), key=lambda x: x[1], reverse=True)
    sr_f_far = sorted(sr_f.items(), key=lambda x: x[1], reverse=False)
    return sr_f_near, sr_f_far


# resets a logger memory and runs it
def frm_n_run(mac, sn):
    try:
        lc = LcBLEFactory.generate(mac)
        ok = 0
        with lc(mac) as lc:
            # sets up logger time, memory, serial number, tests leds
            rv = lc.command(LED_CMD)
            print('\t\tLED --> {}'.format(rv))
            ok += b'ERR' in rv

            rv = lc.command(STATUS_CMD)
            print('\t\tSTS --> {}'.format(rv))
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

            cfg_file = {
                'DFN': 'sxt',
                'TMP': 0, 'PRS': 0,
                'DOS': 1, 'DOP': 1, 'DOT': 1,
                'TRI': 10, 'ORI': 10, 'DRI': 10,
                'PRR': 8,
                'PRN': 4,
                'STM': '2012-11-12 12:14:00',
                'ETM': '2030-11-12 12:14:20',
                'LED': 1
            }
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

            result = lc.command(DO_SENSOR_READINGS_CMD)
            print('\t\tGDO --> {}'.format(result))
            ok += b'ERR' in rv

            # starts the logger
            time.sleep(1)
            rv = lc.command(RUN_CMD)
            print('\t\tRUN --> {}'.format(rv))
            ok += b'ERR' in rv

            # ok != 0 is bad
            return ok

    except ble.BTLEException as ex:
        print('BLE: connect exception --> {}'.format(ex))


def get_ordered_scan_results(dummies=False) -> dict:
    """
    Does a BLE scan and returns friendly results lists
    :param dummies: add a couple dummies for resting
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

    if dummies:
        sr_f[FAKE_MAC_CC26X2] = -10
        sr_f['dummy_2'] = -11

    # nearest: the highest value, less negative
    sr_f_near = sorted(sr_f.items(), key=lambda x: x[1], reverse=True)
    sr_f_far = sorted(sr_f.items(), key=lambda x: x[1], reverse=False)
    return sr_f_near, sr_f_far
