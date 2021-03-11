#!/usr/bin/env python3

import time
import serial
import sys
from serial import SerialException


# hardcoded, since they are FIXED on SixFab hats
PORT_CTRL = '/dev/ttyUSB2'
PORT_DATA = '/dev/ttyUSB1'


def _coord_decode(coord: str):
    # src: stackoverflow 18442158 latitude format
    x = coord.split(".")
    head = x[0]
    deg = head[:-2]
    minutes = '{}.{}'.format(head[-2:], x[1])
    decimal = int(deg) + float(minutes) / 60
    return decimal


def _gps_configure_quectel() -> int:
    """ only needed once, configures Quectel GPS via USB and closes port """
    rv = 0
    sp = None
    try:
        sp = serial.Serial(PORT_CTRL, baudrate=115200, timeout=0.5)
        # ensure GPS disabled, try to enable it
        sp.write(b'AT+QGPSEND\r\n')
        sp.write(b'AT+QGPSEND\r\n')
        sp.write(b'AT+QGPS=1\r\n')
        # ignore echo
        sp.readline()
        ans = sp.readline()
        rv = 0 if ans == b'OK\r\n' else 2
        # errors: 504 (already on), 505 (not activated)
        if ans.startswith(b'+CME ERROR: '):
            rv = ans.decode()[-3]
    except (FileNotFoundError, SerialException) as ex:
        rv = 1
    finally:
        if sp:
            sp.close()
        return rv


if __name__ == '__main__':
    retries = 0

    # try to enable GPS port
    while 1:
        if retries == 3:
            e = '[ ER ] GPS Quectel failure init, retry {}'
            print(e.format(retries + 1))
            sys.exit(1)
        if _gps_configure_quectel() == 0:
            print('[ OK ] GPS Quectel initialization success')
            break
        time.sleep(1)

    # try to get GPS frames
    sp, _till, i = None, 20, 0
    s = '[ .. ] GPS Quectel, will check for frames up to {} seconds...'
    print(s.format(_till))
    try:
        sp = serial.Serial(PORT_DATA, baudrate=115200, timeout=0.1)
        _till = time.perf_counter() + _till
        while True:
            if time.perf_counter() > _till:
                e = '[ ER ] GPS Quectel, could not get any data frame'
                print(e)
                break
            data = sp.readline()
            if (i % 10) == 0:
                print('.')
            if b'$GPRMC' in data:
                data = data.decode()
                s = data.split(",")
                if s[2] == 'V':
                    continue
                if s[3] and s[5]:
                    print('[ -> ] {}'.format(data))
                    lat, lon = _coord_decode(s[3]), _coord_decode(s[5])
                    print('[ OK ] GPS Quectel data success: {}, {}'.format(lat, lon))
                    break
    except SerialException as se:
        print(se)
    finally:
        if sp:
            sp.close()          
 
