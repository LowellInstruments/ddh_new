import datetime
import logzero
from logzero import logger
import http.client
import subprocess as sp
import shlex
import os
import glob
import time
from random import random
from logzero import logger as console_log
from ddh.settings import ctx
from mat.crc import calculate_local_file_crc
from mat.data_converter import DataConverter, default_parameters
import json
from socket import AF_INET, SOCK_DGRAM
import socket
import struct


def emit_status(sig, s):
    if sig:
        sig.status.emit(s)


def emit_error(sig, e):
    if sig:
        sig.status.emit(e)


def emit_update(sig, u):
    if sig:
        sig.status.emit(u)


def rpi_set_brightness(v):
    """ adjusts DDH screen brightness """

    v *= 127
    v = 50 if v < 50 else v
    v = 255 if v > 250 else v
    b = '/sys/class/backlight/rpi_backlight/brightness"'
    s = 'sudo bash -c "echo {} > {}'.format(str(v), b)
    o = sp.DEVNULL
    sp.run(shlex.split(s), stdout=o, stderr=o)


def linux_set_datetime(t_str):
    # e.g. $ date -s "19 APR 2012 11:14:00"

    s = 'sudo date -s "{}"'.format(t_str)
    o = sp.DEVNULL
    rv = sp.run(shlex.split(s), stdout=o, stderr=o)
    return rv.returncode == 0


def get_ntp_time(host="pool.ntp.org"):

    # credit: Matt Crampton
    try:
        sk = socket.socket(AF_INET, SOCK_DGRAM)
        sk.settimeout(.3)
    except (OSError, Exception) as ex:
        print('SYS: ' + str(ex))
        return

    port, buf = 123, 1024
    address = (host, port)
    msg = '\x1b' + 47 * '\0'
    rv = False
    time_1970 = 2208988800
    t_ntp = 0
    for _ in range(10):
        try:
            sk.sendto(msg.encode(), address)
            msg, address = sk.recvfrom(buf)
            t_ntp = struct.unpack("!12I", msg)[10]
            # ntp takes care of timezones, no HH adjust
            t_ntp -= time_1970
            t_ntp = t_ntp if t_ntp else None
            rv = True
            break
        except (OSError, Exception):
            time.sleep(random())

    if sk.connect_ex(address):
        sk.shutdown(socket.SHUT_RDWR)
        sk.close()

    if not rv:
        e = 'CLK: timeout in {}'.format(__name__)
        console_log.error(e)
        return None
    return t_ntp


def linux_is_net_ok():
    """ returns True if we have internet connectivity """

    for _ in range(5):
        conn = http.client.HTTPConnection('www.google.com', timeout=.3)
        try:
            conn.request('HEAD', '/')
            conn.close()
            return True
        except (OSError, Exception):
            conn.close()
            return False
    return False


def pre_rm_csv(fol, pre_rm=False):
    """ util to remove CSV files """

    if not pre_rm:
        return
    ff = linux_ls_by_ext(fol, 'csv')
    for _ in ff:
        os.remove(_)
        print('removed {}'.format(os.path.basename(_)))


def linux_ls_by_ext(fol, extension):
    """ recursively collect all logger files w/ indicated extension """

    if not fol:
        return []
    if os.path.isdir(fol):
        wildcard = fol + '/**/*.' + extension
        return glob.glob(wildcard, recursive=True)


def update_dl_folder_list(d):
    """ gets updated logger folders list """

    if os.path.isdir(d):
        f_l = [f.path for f in os.scandir(d) if f.is_dir()]
        return f_l
    else:
        os.makedirs(d, exist_ok=True)


def json_check_metrics(j):
    """ ensure we do not ask for too much metrics """

    try:
        with open(j) as f:
            cfg = json.load(f)
            assert len(cfg['metrics']) <= 2
    except (FileNotFoundError, TypeError, json.decoder.JSONDecodeError):
        console_log.error('SYS: error reading ddh.json config file')
        return False
    return True


def json_get_ship_name(j):
    try:
        with open(j) as f:
            cfg = json.load(f)
            return cfg['ship_name']
    except TypeError:
        return 'Unnamed ship'


def json_set_plot_units(j):
    with open(j) as f:
        cfg = json.load(f)
    assert cfg['units']
    ctx.plt_units = cfg['units']


def json_get_forget_time_secs(j):
    with open(j) as f:
        return int(json.load(f)['forget_time'])


def json_get_forget_time_at_sea_secs(j):
    with open(j) as f:
        return int(json.load(f)['forget_time_at_sea'])


def json_get_macs(j):
    """ gets list of macs in ddh.json file """

    try:
        with open(j) as f:
            cfg = json.load(f)
            known = cfg['db_logger_macs'].keys()
            return [x.lower() for x in known]
    except TypeError:
        return 'error json_get_macs()'


def json_get_pairs(j):
    """ gets list of pairs {mac, names} in ddh.json file """

    try:
        with open(j) as f:
            cfg = json.load(f)
            # macs not lowered()
            return cfg['db_logger_macs']
    except TypeError:
        return 'error json_get_macs()'


def json_get_metrics(j):
    with open(j) as f:
        cfg = json.load(f)
        assert 0 < len(cfg['metrics']) <= 2
        return cfg['metrics']


def json_get_span_dict(j):
    with open(j) as f:
        cfg = json.load(f)
        assert cfg['span_dict']
        return cfg['span_dict']


def json_get_hci_if(j):
    with open(j) as f:
        cfg = json.load(f)
        assert 0 <= cfg['hci_if'] <= 1
        return cfg['hci_if']


def _mac_dns_no_case(j, mac):
    """ gets mac from ddh.json file and return its name case-sensitive """

    try:
        with open(j) as f:
            cfg = json.load(f)
            return cfg['db_logger_macs'][mac]
    except (FileNotFoundError, TypeError, KeyError):
        return None


def json_mac_dns(j, mac):
    """ returns non-case-sensitive logger name (known) or mac (unknown) """

    name = _mac_dns_no_case(j, mac.lower())
    # check for both upper() and lower() cases
    if not name:
        name = _mac_dns_no_case(j, mac.upper())
    rv = name if name else mac
    return rv


def get_mac_from_folder_path(fol):
    """ returns '11:22:33' from 'dl_files/11-22-33' """

    try:
        return fol.split('/')[-1].replace('-', ':')
    except (ValueError, Exception):
        return None


def get_folder_path_from_mac(mac):
    """ returns 'dl_files/11-22-33' from '11:22:33' """

    fol = ctx.app_dl_folder
    fol = fol / '{}/'.format(mac.replace(':', '-').lower())
    return fol


def lid_to_csv(fol, suffix, sig, files_to_ignore=[]) -> (bool, list):
    """ converts depending on fileX_suffix.lid is an existing file """

    # valid_suffixes = ('_DissolvedOxygen', '_Temperature', '_Pressure')
    valid_suffixes = ('_DissolvedOxygen', )
    assert suffix in valid_suffixes
    err_files = []

    if not os.path.exists(fol):
        return False, err_files

    # prepare conversion
    parameters = default_parameters()
    lid_files = linux_ls_by_ext(fol, 'lid')
    all_ok = True

    for f in lid_files:
        # prevents continuous warnings on same files
        if f in files_to_ignore:
            continue
        _ = '{}{}.csv'.format(f.split('.')[0], suffix)
        if os.path.exists(_):
            # print('file {} already exists'.format(_))
            continue

        try:
            DataConverter(f, parameters).convert()
            s = 'converted OK -> {}'.format(f)
            sig.status.emit(s)
        except (ValueError, Exception) as ve:
            all_ok = False
            err_files.append(f)
            e = 'error converting {} -> {}'.format(f, ve)
            sig.error.emit(e)

    return all_ok, err_files


def create_folder(mac, fol):
    """ mkdir folder based on mac without ':' characters but '-' """

    fol = fol / '{}/'.format(mac.replace(':', '-').lower())
    os.makedirs(fol, exist_ok=True)
    return fol


def check_local_file_exists(file_name, size, fol):
    path = os.path.join(fol, file_name)
    if os.path.isfile(path):
        if os.path.getsize(path) == size:
            return True
    return False


def check_local_file_integrity(file_name, fol, remote_crc):
    """ calculates local file name CRC and compares to parameter """

    # remote_crc: logger's one, crc: local one
    path = os.path.join(fol, file_name)
    crc = calculate_local_file_crc(path)
    crc = crc.lower()
    # remote_crc: [b'CRC', b'08eac2e456']
    if len(remote_crc) != 2:
        return False, crc
    if len(remote_crc[1]) != 10:
        return False, crc
    # b'08eac2e456' -> 'eac2e456'
    remote_crc = remote_crc[1].decode()[2:].lower()
    return crc == remote_crc, crc


def rm_folder(mac):
    import shutil
    fol = ctx.app_dl_folder
    fol = fol / '{}/'.format(mac.replace(':', '-').lower())
    shutil.rmtree(fol, ignore_errors=True)


def rm_plot_db():
    """ removes plot database file """

    p = ctx.db_plt
    if os.path.exists(p):
        os.remove(p)


def setup_app_log(path_to_log_file: str):
    """ setups application logging """

    log = path_to_log_file
    logzero.logfile(log, maxBytes=int(1e6), backupCount=3, mode='a')
    fmt = '%b %d %H:%M:%S'
    _t = datetime.datetime.now().strftime(fmt)
    s = '\n\n\n'
    logger.debug(s)
    s = '==== DDH booted on {} ===='.format(_t)
    logger.debug(s)


def update_cnv_log_err_file(path_to_log_file, _err_reasons):
    """ puts LID file conversion errors to log file """

    if not _err_reasons:
        return

    with open(path_to_log_file, 'w') as f:
        for _ in _err_reasons:
            fmt = '%b %d %H:%M:%S'
            _t = datetime.datetime.now().strftime(fmt)
            s = '{}  {}'.format(_t, _)
            f.write(str(s))


def wait_boot_signal(w, ev, s):
    """ threads do not proceed until receiving ev """

    ev.wait()
    t = random() * 1
    time.sleep(1 + t)
    _ = 'SYS: {} thread started'.format(s)
    w.sig_aws.status.emit(_)


def is_float(s: str):
    try:
        float(s)
        return True
    except ValueError:
        return False


# test robustness
if __name__ == '__main__':
    while 1:
        t = get_ntp_time()
        print(t)
        time.sleep(1)
