import os
import bluepy.btle as ble
from mat.logger_controller_ble import LoggerControllerBLE
from mat.logger_controller import STOP_CMD
from mat.crc import calculate_local_file_crc
from mat.data_converter import DataConverter, default_parameters


def cnv(path):
    try:
        print('\t\tConverting --> {}'.format(path), end='')
        parameters = default_parameters()
        converter = DataConverter(path, parameters)
        converter.convert()
        print('  ok')
    except Exception as ex:
        print('  error')
        print(ex)


def _ensure_rm_prev_file(path):
    try:
        os.remove(path)
    except OSError:
        pass


def dwg(mac):
    try:
        with LoggerControllerBLE(mac) as lc:

            # status, stop and DIR
            c = STOP_CMD
            r = lc.command(c)
            print('{} --> {}'.format(c, r))
            ls = lc.ls_ext(b'lid')
            print('files inside logger -> '.format(ls))

            # dwg & dwl
            for file_name, file_size in ls.items():
                _ensure_rm_prev_file(file_name)
                print('downloading {}...'.format(file_name))
                data = lc.dwg_file(file_name, '.', file_size)
                if data:
                    cd = calculate_local_file_crc(file_name)
                    cr = lc.command('CRC', file_name)
                    print('CRC downloaded file = {}'.format(cd))
                    print('CRC at remote files = {}'.format(cr))
                    cnv(file_name)
                else:
                    print('download {} failed'.format(file_name))
                    return

    except ble.BTLEException as ex:
        print('BLE: connect exception --> {}'.format(ex))


if __name__ == '__main__':
    my_mac = '60:77:71:22:C8:08'
    dwg(my_mac)
