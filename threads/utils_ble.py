import datetime
import json
import pathlib
import time
from mat.logger_controller_ble import LoggerControllerBLE
from threads.utils import rm_folder, create_folder, exists_file, json_mac_dns
from mat.logger_controller import (
    RWS_CMD,
    SWS_CMD, STATUS_CMD
)
from settings import ctx
from threads.utils_gps import sync_pos


def _time_to_display(t):
    t = t if t <= 3 else 3
    time.sleep(t)


def emit_scan_pre(sig, s):
    if sig:
        sig.ble_scan_pre.emit(s)


def emit_scan_post(sig, n):
    if sig:
        sig.ble_scan_post.emit(n)


def emit_status(sig, s):
    if sig:
        sig.ble_status.emit(s)


def emit_debug(sig, s):
    if sig:
        sig.ble_debug.emit(s)


def emit_error(sig, e):
    if sig:
        sig.ble_error.emit(e)


def emit_logger_pre(sig):
    if sig:
        sig.ble_logger_pre.emit()


def emit_logger_post(sig, ok, s, mac):
    if sig:
        sig.ble_logger_post.emit(ok, s, mac)


def emit_logger_plot_req(sig, mac):
    if sig:
        sig.ble_logger_plot_req.emit(mac)


def emit_file_pre(sig, name, size, num, total, mm):
    if sig:
        sig.ble_file_pre.emit(name, size, num, total, mm)


def emit_file_post(sig, speed):
    if sig:
        sig.ble_file_post.emit(speed)


def emit_deployed(sig, mac, lat, lon):
    if sig:
        sig.ble_deployed.emit(mac, lat, lon)


def emit_session_pre(sig, mac, c, n):
    if sig:
        sig.ble_session_pre.emit(mac, c, n)


def emit_dl_warning(sig, w):
    if not sig:
        return
    if w:
        j = ctx.json_file
        w = json_mac_dns(j, w)
        w = '{} not deployed'.format(w)
    sig.ble_dl_warning.emit(w)


def emit_session_post(sig, s):
    if sig:
        sig.ble_session_post.emit(s)


def _die(d):
    raise AppBLEException(d)


def _show(rv, sig):
    txt = 'BLE: {}'.format(rv)
    emit_status(sig, txt)


def _error(rv, sig):
    txt = 'DIE: {}'.format(rv)
    emit_error(sig, txt)


def _ok_or_die(w, rv, sig):
    if rv != w:
        _error((rv, w), sig)
        _die(rv)
    _show(rv, sig)


def _logger_already_stopped(lc):
    rv = lc.command(STATUS_CMD)
    return rv == [b'STS', b'0201']


def _logger_sws(lc, sig, g):
    """ stop with string """

    rv = _logger_already_stopped(lc)
    if rv:
        s = 'BLE: no SWS required'
        emit_status(sig, s)
        return

    # logger running or delayed, need to stop
    lat = g[0] if g else 'N/A'
    lon = g[1] if g else 'N/A'
    s = '{}{}'.format(lat, lon)
    t = 'BLE: SWS coordinates {}'.format(s)
    for _ in range(10):
        # slightly largest than worst sensor measurement
        rv = lc.command(SWS_CMD, s)
        if rv == [b'SWS', b'00']:
            emit_status(sig, t)
            return
        time.sleep(.5)
    _die(rv)


def _logger_time_check(lc, sig=None):
    # command: GTM
    rv = lc.get_time()
    _show(rv, sig)

    # protection
    if rv is None:
        _die(__name__)

    # command: STM only if needed
    d = datetime.datetime.now() - rv
    rv = 'time sync not needed'
    if abs(d.total_seconds()) > 60:
        rv = lc.sync_time()
        _ok_or_die([b'STM', b'00'], rv, sig)
        rv = 'time synced {}'.format(lc.get_time())
    _show(rv, sig)


def _logger_ls(lc, fol, sig=None, pre_rm=False):
    # fol modified to not contain ':'
    mac = lc.per.addr
    if pre_rm:
        rm_folder(mac)
    fol = create_folder(mac, fol)

    # merge 2 DIR listings in a dictionary
    lid_f = lc.ls_ext(b'lid')
    s = 'BLE: DIR lid {}'.format(lid_f)
    emit_status(sig, s)
    gps_f = lc.ls_ext(b'gps')
    s = 'BLE: DIR gps {}'.format(gps_f)
    emit_status(sig, s)
    if lid_f == [b'ERR'] or gps_f == [b'ERR']:
        return None
    files = lid_f
    files.update(gps_f)
    return fol, files


def _logger_get_files(lc, sig, folder, files):
    mac = lc.per.addr
    num_to_get = 0
    name_n_size = {}
    b_total = 0

    # skip files we already have locally
    for each in files.items():
        name = each[0]
        size = each[1]

        if size == 0:
            s = 'not downloading {}, size 0'.format(name)
            emit_status(sig, s)
            continue

        if not exists_file(name, size, folder):
            name_n_size[name] = size
            num_to_get += 1
            b_total += size

    # statistics
    got = 0
    b_left = b_total
    s = 'BLE: {} has {} files for us'.format(mac, num_to_get)
    emit_status(sig, s)

    # download files one by one
    num = 1
    for name, size in name_n_size.items():
        mm = ((b_left // 5000) // 60) + 1
        b_left -= size
        s = 'BLE: get {}, {} B'.format(name, size)
        emit_status(sig, s)
        emit_file_pre(sig, name, b_total, num, num_to_get, mm)
        num += 1

        # x-modem download
        s_t = time.time()
        if lc.get_file(name, folder, size, sig.ble_dl_step):
            s = 'BLE: got {}'.format(name)
            emit_status(sig, s)
        else:
            s = 'BLE: can\'t get {}, size {}'.format(name, size)
            emit_error(sig, s)
            # continue
            return False

        # check got file ok
        if exists_file(name, size, folder):
            got += 1
            speed = size / (time.time() - s_t)
            emit_file_post(sig, speed)

    # logger was downloaded ok
    _ = 'almost done, '
    if got > 0:
        s = 'we got {} file(s)'.format(got)
    elif got == 0:
        s = 'no files to get'
    else:
        s = 'we already had all files'
    s = '{}\n{}'.format(_, s)
    emit_logger_post(sig, True, s, mac)
    return num_to_get == got


def _logger_rws(lc, sig, g):
    lat = g[0] if g else 'N/A'
    lon = g[1] if g else 'N/A'
    g = '{}{}\n'.format(lat, lon)
    rv = lc.command(RWS_CMD, g)
    _ok_or_die([b'RWS', b'00'], rv, sig)
    emit_deployed(sig, lc.per.addr, lat, lon)


def _ddh_get_gps():
    return sync_pos(sig=None, timeout=10)


def _logger_plot(mac, sig):
    emit_logger_plot_req(sig, mac)


def _get_cfg_file(lc, sig):
    for _ in range(3):
        rv = lc.ls_ext(b'.cfg')
        s = 'BLE: DIR cfg {}'.format(rv)
        emit_status(sig, s)
        if rv:
            return rv
        time.sleep(1)
    return None


def _logger_re_setup(lc, sig):
    rv = _get_cfg_file(lc, sig)
    size = 0
    try:
        size = rv['MAT.cfg']
    except (KeyError, TypeError):
        # when logger has no MAT.cfg
        _die('no MAT.cfg to download')

    # download MAT.cfg
    if not size:
        _die('no MAT.cfg size')
    s = 'BLE: getting MAT.cfg'
    emit_status(sig, s)
    dff = ctx.dl_files_folder
    rv = lc.get_file('MAT.cfg', dff, size, None)
    if not rv:
        _die('error downloading MAT.cfg')
    s = 'BLE: got MAT.cfg'
    emit_status(sig, s)

    # ensure MAT.cfg suitable for CFG command
    p = pathlib.Path(dff / 'MAT.cfg')
    with open(p) as f:
        cfg_dict = json.load(f)
    if not cfg_dict:
        _die('no MAT.cfg dict')

    # if we reach here, we are doing ok
    rv = lc.command('FRM')
    _ok_or_die([b'FRM', b'00'], rv, sig)

    # ex: PRR = 16, PRN = 65535 --> 4095 > SRI = 3600
    rv = lc.send_cfg(cfg_dict)
    _ok_or_die([b'CFG', b'00'], rv, sig)


# super function called from BLE thread
def logger_download(mac, fol, hci_if, sig=None):
    try:
        with LoggerControllerBLE(mac, hci_if) as lc:
            g = _ddh_get_gps()
            _logger_sws(lc, sig, g)
            _logger_time_check(lc, sig)
            fol, ls = _logger_ls(lc, fol, sig, pre_rm=False)
            got_all = _logger_get_files(lc, sig, fol, ls)
            if got_all:
                _logger_re_setup(lc, sig)
                _logger_rws(lc, sig, g)
                s = 'logger done'
                emit_logger_post(sig, True, s, mac)
                _logger_plot(mac, sig)
                emit_dl_warning(sig, '')
                blacklist_as_done = True
            else:
                e = 'logger {} not done yet'.format(mac)
                emit_logger_post(sig, False, e, mac)
                emit_dl_warning(sig, mac)
                emit_error(sig, e)
                blacklist_as_done = False
            _time_to_display(2)
            return blacklist_as_done

    # my exception, such as no MAT.cfg file
    except AppBLEException as ex:
        e = 'error at {}, will retry'.format(ex)
        emit_logger_post(sig, False, e, mac)
        emit_error(sig, e)
        emit_dl_warning(sig, mac)
        return False

    # such as None.command()
    except AttributeError as ae:
        emit_error(sig, 'error: {}'.format(ae))
        emit_dl_warning(sig, mac)
        return False


class AppBLEException(Exception):
    pass
