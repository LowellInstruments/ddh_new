import datetime
import json
import pathlib
import time
from json import JSONDecodeError
from ddh.settings import ctx
from ddh.threads.utils import (
    rm_folder,
    create_folder,
    check_local_file_exists,
    emit_status,
    check_local_file_integrity, is_float, get_folder_path_from_mac
)
from ddh.threads.utils_gps_quectel import utils_gps_get_one_lat_lon_dt, utils_gps_backup_get
from mat.logger_controller import (
    RWS_CMD,
    SWS_CMD, STATUS_CMD
)
from mat.logger_controller_ble import ERR_MAT_ANS, FORMAT_CMD, CRC_CMD, WAKE_CMD
from mat.logger_controller_ble_factory import LcBLEFactory


def _time_to_display(t):
    t = t if t <= 3 else 3
    time.sleep(t)


def _die(d):
    raise AppBLEException(d)


def _show(rv, sig):
    txt = 'BLE: {}'.format(rv)
    sig.status.emit(txt)


def _error(rv, sig):
    txt = 'DIE: {}'.format(rv)
    sig.error.emit(txt)


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

    # logger running or delayed, we gonna stop it
    lat, lon, _ = g if g else (None, ) * 3
    if lat and is_float(lat) and lon and is_float(lon):
        lat = '{:+.6f}'.format(float(lat))
        lon = '{:+.6f}'.format(float(lon))
    else:
        lat, lon = 'N/A', 'N/A'

    # SWS parameter contains no comma
    g = '{}{}'.format(lat, lon)
    for _ in range(10):
        rv = lc.command(SWS_CMD, '{}'.format(g))
        if rv == [b'SWS', b'00']:
            _show('SWS coordinates {}'.format(g), sig)
            return
        time.sleep(.5)
    _die(rv)


def _logger_time_check(lc, sig=None):
    # command: GTM
    dt = lc.get_time()
    _show(dt, sig)

    # protection
    if dt is None:
        _die(__name__)

    # command: STM only if dates off by > 1 minute
    diff = datetime.datetime.now() - dt
    s = 'time sync not needed'
    if abs(diff.total_seconds()) > 60:
        rv = lc.sync_time()
        _ok_or_die([b'STM', b'00'], rv, sig)
        s = 'time synced {}'.format(lc.get_time())
    _show(s, sig)


def _logger_ls(lc, fol, sig=None, pre_rm=False):

    # create folder when not exists
    assert ':' not in str(fol)
    mac = lc.per.addr
    if pre_rm:
        rm_folder(mac)
    fol = create_folder(mac, fol)

    # merge 2 DIR listings in a dictionary
    lid_f = lc.ls_lid()
    s = 'BLE: DIR lid {}'.format(lid_f)
    emit_status(sig, s)
    gps_f = lc.ls_ext(b'gps')
    s = 'BLE: DIR gps {}'.format(gps_f)
    emit_status(sig, s)
    err = ERR_MAT_ANS.encode()
    if lid_f == err or gps_f == err:
        return None
    files = lid_f
    files.update(gps_f)
    return fol, files


# def _logger_get_files(lc, sig, folder, files):
#     mac, num_to_get, got = lc.per.addr, 0, 0
#     name_n_size, b_total = {}, 0
#
#     # filter what we'll get, omit locally existing ones
#     for each in files.items():
#         name, size = each[0], int(each[1])
#
#         if size == 0:
#             _show('not getting {}, size 0'.format(name), sig)
#             continue
#
#         if not check_local_file_exists(name, size, folder):
#             name_n_size[name] = size
#             num_to_get += 1
#             b_total += size
#
#     # statistics
#     b_left = b_total
#     _show('{} has {} files for us'.format(mac, num_to_get), sig)
#
#     # download files one by one
#     label = 1
#     for name, size in name_n_size.items():
#         mm = ((b_left // 5000) // 60) + 1
#         b_left -= size
#         _show('get {}, {} B'.format(name, size), sig)
#         sig.file_pre.emit(name, b_total, label, num_to_get, mm)
#         label += 1
#
#         # x-modem download
#         s_t = time.time()
#         if not lc.get_file(name, folder, size, sig.dl_step):
#             e = 'BLE: cannot get {}, size {}'
#             _error(e.format(name, size), sig)
#             return False
#
#         # check file CRC
#         crc = lc.command('CRC', name)
#         rv, l_crc = check_local_file_integrity(name, folder, crc)
#         # s = 'BLE: {} remote crc {} | local crc {}'
#         # emit_status(sig, s.format(name, crc, l_crc))
#         if not rv:
#             _error('bad crc on {}'.format(name), sig)
#             return False
#         emit_status(sig, 'BLE: got {} w/ good CRC'.format(name))
#
#         # show CRC and statistics
#         got += 1
#         speed = size / (time.time() - s_t)
#         sig.file_post.emit(speed)
#
#     # logger was downloaded ok
#     _ = 'almost done, '
#     if got > 0:
#         s = 'got {} file(s)'.format(got)
#     elif got == 0:
#         s = 'no files to get'
#     else:
#         s = 'already had all files'
#     s = '{}\n{}'.format(_, s)
#     sig.logger_post.emit(True, s, mac)
#
#     # success condition
#     return num_to_get == got


def _logger_dwg_files(lc, sig, folder, files):
    mac, num_to_dwg, dwg_ed = lc.per.addr, 0, 0
    name_n_size, b_total = {}, 0

    # filter what we'll get, omit locally existing ones
    for each in files.items():
        name, size = each[0], int(each[1])

        if size == 0:
            _show('not downloading {}, size 0'.format(name), sig)
            continue

        if not check_local_file_exists(name, size, folder):
            name_n_size[name] = size
            num_to_dwg += 1
            b_total += size

    # statistics
    b_left = b_total
    _show('{} has {} files for us'.format(mac, num_to_dwg), sig)

    # download files one by one
    label = 1
    for name, size in name_n_size.items():
        mm = ((b_left // 5000) // 60) + 1
        b_left -= size
        _show('dwg {}, {} B'.format(name, size), sig)
        sig.file_pre.emit(name, b_total, label, num_to_dwg, mm)
        label += 1

        # x-modem download
        s_t = time.time()

        if not lc.dwg_file(name, folder, size, sig.dl_step):
            e = 'BLE: cannot download {}, size {}'
            _error(e.format(name, size), sig)
            return False

        # check file CRC
        crc = lc.command('CRC', name)
        rv, l_crc = check_local_file_integrity(name, folder, crc)
        # s = 'BLE: {} remote crc {} | local crc {}'
        # emit_status(sig, s.format(name, crc, l_crc))
        if not rv:
            _error('crc mismatch for {}'.format(name), sig)
            _error('local crc {} remote crc {}'.format(l_crc, crc), sig)
            return False
        emit_status(sig, 'BLE: got {} w/ good CRC'.format(name))

        # show CRC and statistics
        dwg_ed += 1
        speed = size / (time.time() - s_t)
        sig.file_post.emit(speed)

    # logger was downloaded ok
    _ = 'almost done, '
    if dwg_ed > 0:
        s = 'got {} file(s)'.format(dwg_ed)
    elif dwg_ed == 0:
        s = 'no files to get'
    else:
        s = 'already had all files'
    s = '{}\n{}'.format(_, s)
    sig.logger_post.emit(True, s, mac)

    # success condition
    return num_to_dwg == dwg_ed


def _logger_rws(lc, sig, g):
    lat, lon, _ = g if g else (None, ) * 3
    if lat and is_float(lat) and lon and is_float(lon):
        lat = '{:+.6f}'.format(float(lat))
        lon = '{:+.6f}'.format(float(lon))
    else:
        lat, lon = 'N/A', 'N/A'

    g = '{}{}'.format(lat, lon)
    s = 'BLE: RWS coordinates {}'.format(g)
    sig.status.emit(s)
    rv = lc.command(RWS_CMD, g)
    _ok_or_die([b'RWS', b'00'], rv, sig)
    sig.deployed.emit(lc.per.addr, str(lat), str(lon))


def _logger_plot(mac, sig):
    sig.logger_plot_req.emit(mac)


def _dir_cfg(lc, sig):
    # sleep helps, logger may still in previous x-modem
    time.sleep(1)
    rv = lc.ls_ext(b'.cfg')
    _show('DIR cfg {}'.format(rv), sig)
    return rv


def _ensure_wake_mode_is_on(lc, sig):
    rv = lc.command(WAKE_CMD)
    if len(rv) != 2:
        _die('sending wake mode 1 failed')
    wak_is_on = rv[1].decode()[-1]
    if wak_is_on == '0':
        rv = lc.command(WAKE_CMD)
        if len(rv) != 2:
            _die('sending wake mode 2 failed')
    wak_is_on = rv[1].decode()[-1]
    if wak_is_on == '1':
        _show('wake mode enabled', sig)
        return
    _die('could not enable wake mode')


def _logger_re_setup(lc, sig):
    """ get logger's MAT.cfg, formats mem, re-sends MAT.cfg """
    _MC = 'MAT.cfg'

    size, rv = 0, _dir_cfg(lc, sig)
    try:
        size = rv[_MC]
    except (KeyError, TypeError):
        e = 'no {} in logger to re-setup'
        _die(e.format(_MC))
    if not size:
        _die('no {} size'.format(_MC))

    # download MAT.cfg
    dff = get_folder_path_from_mac(lc.address)
    _show('downloading {}...'.format(_MC), sig)

    if not lc.dwg_file(_MC, dff, size, None):
        _die('error downloading {}'.format(_MC))

    # check MAT.cfg file
    crc = lc.command(CRC_CMD, _MC)
    rv, l_crc = check_local_file_integrity(_MC, dff, crc)
    if not rv:
        _error('crc mismatch for {}'.format(_MC), sig)
        _error('local crc {} remote crc {}'.format(l_crc, crc), sig)
        _die('error CRC for {}'.format(_MC))
    _show('got {}'.format(_MC), sig)

    # ensure MAT.cfg suitable for CFG command
    try:
        with open(pathlib.Path(dff / _MC)) as f:
            cfg_dict = json.load(f)
            if not cfg_dict:
                _die('no {} dict'.format(_MC))
    except FileNotFoundError:
        _die('cannot load downloaded {}'.format(_MC))
    except JSONDecodeError:
        _die('cannot decode downloaded {}'.format(_MC))

    # format the logger
    rv = lc.command(FORMAT_CMD)
    _ok_or_die([b'FRM', b'00'], rv, sig)

    # re-config the logger
    rv = lc.send_cfg(cfg_dict)
    _ok_or_die([b'CFG', b'00'], rv, sig)

    # enable wake-up mode
    _ensure_wake_mode_is_on(lc, sig)


def logger_download(mac, fol, hci_if, sig=None):
    """ downloads logger files and re-setups it """

    try:
        lc = LcBLEFactory.generate(mac)

        with lc(mac, hci_if) as lc:
            # g -> (lat, lon, ignored datetime object)
            g = utils_gps_get_one_lat_lon_dt(timeout=5)
            if not g:
                g = utils_gps_backup_get()
            _logger_sws(lc, sig, g)
            _logger_time_check(lc, sig)

            # DIR logger files and get them
            fol, ls = _logger_ls(lc, fol, sig, pre_rm=False)
            # got_all = _logger_get_files(lc, sig, fol, ls)
            got_all = _logger_dwg_files(lc, sig, fol, ls)

            # :) got all files
            if got_all:
                _logger_re_setup(lc, sig)
                _logger_rws(lc, sig, g)
                sig.logger_post.emit(True, 'logger done', mac)

                # plot it
                _logger_plot(mac, sig)
                _time_to_display(2)
                return True, g

            # :( did NOT get all files
            e = 'logger {} not done yet'.format(mac)
            sig.logger_post.emit(False, e, mac)
            sig.error.emit(e.format(mac))
            return False, None

    # my exception, ex: no MAT.cfg file
    except AppBLEException as ex:
        e = 'error: {}, will retry'.format(ex)
        # e: ends up in history tab
        sig.logger_post.emit(False, e, mac)
        sig.error.emit(e)
        return False, None

    # bluepy or python exception, ex: None.command()
    except AttributeError as ae:
        sig.error.emit('error: {}'.format(ae))
        return False, None


class AppBLEException(Exception):
    # used 10 lines above
    pass
