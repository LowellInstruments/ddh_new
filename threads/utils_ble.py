import datetime
import json
import pathlib
import time
from mat.logger_controller_ble import LoggerControllerBLE, ERR_MAT_ANS
from threads.utils import rm_folder, create_folder, exists_file, emit_status, emit_error
from mat.logger_controller import (
    RWS_CMD,
    SWS_CMD, STATUS_CMD
)
from settings import ctx
from threads.utils_gps_internal import gps_get_one_lat_lon_dt


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

    # logger running or delayed, need to stop
    lat = '{:+.6f}'.format(float(g[0])) if g else 'N/A'
    lon = '{:+.6f}'.format(float(g[1])) if g else 'N/A'
    t = 'BLE: SWS coordinates {}, {}'.format(lat, lon)
    for _ in range(10):
        # SWS parameter goes altogether without comma
        rv = lc.command(SWS_CMD, '{}{}'.format(lat, lon))
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
        sig.file_pre.emit(name, b_total, num, num_to_get, mm)
        num += 1

        # x-modem download
        s_t = time.time()
        if lc.get_file(name, folder, size, sig.dl_step):
            emit_status(sig, 'BLE: got {}'.format(name))
        else:
            e = 'BLE: can\'t get {}, size {}'.format(name, size)
            emit_error(sig, e)
            # continue
            return False

        # check got file ok
        if exists_file(name, size, folder):
            got += 1
            speed = size / (time.time() - s_t)
            sig.file_post.emit(speed)

    # logger was downloaded ok
    _ = 'almost done, '
    if got > 0:
        s = 'we got {} file(s)'.format(got)
    elif got == 0:
        s = 'no files to get'
    else:
        s = 'already had all files'
    s = '{}\n{}'.format(_, s)
    sig.logger_post.emit(True, s, mac)

    return num_to_get == got


def _logger_rws(lc, sig, g):
    lat = float(g[0]) if g else 'N/A'
    lon = float(g[1]) if g else 'N/A'
    g = '{:+.6f}{:+.6f}'.format(lat, lon)
    s = 'BLE: RWS coordinates {}'.format(g)
    sig.status.emit(s)
    rv = lc.command(RWS_CMD, g)
    _ok_or_die([b'RWS', b'00'], rv, sig)
    sig.deployed.emit(lc.per.addr, str(lat), str(lon))


def _logger_plot(mac, sig):
    sig.logger_plot_req.emit(mac)


def _dir_cfg(lc, sig):
    # helps, x-modem may still be ending in logger
    time.sleep(1)
    rv = lc.ls_ext(b'.cfg')
    s = 'BLE: DIR cfg {}'.format(rv)
    emit_status(sig, s)
    return rv


def _logger_re_setup(lc, sig):
    rv = _dir_cfg(lc, sig)
    size = 0
    try:
        size = rv['MAT.cfg']
    except (KeyError, TypeError):
        # no MAT.cfg within logger, that is an error
        _die('no MAT.cfg to download')

    # download MAT.cfg
    if not size:
        _die('no MAT.cfg size')
    s = 'BLE: getting MAT.cfg'
    emit_status(sig, s)
    dff = ctx.app_dl_folder
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


def logger_download(mac, fol, hci_if, sig=None):
    try:
        with LoggerControllerBLE(mac, hci_if) as lc:
            # g-> (lat, lon, datetime object)
            g = gps_get_one_lat_lon_dt()
            _logger_sws(lc, sig, g)
            _logger_time_check(lc, sig)

            # DIR logger files and get them
            fol, ls = _logger_ls(lc, fol, sig, pre_rm=False)
            got_all = _logger_get_files(lc, sig, fol, ls)

            # got all files, everything went perfect
            if got_all:
                _logger_re_setup(lc, sig)
                _logger_rws(lc, sig, g)
                sig.logger_post.emit(True, 'logger done', mac)

                # plot it
                _logger_plot(mac, sig)
                _time_to_display(2)
                return True, g

            # mmm, we did NOT get all files
            e = 'logger {} not done yet'
            sig.logger_post.emit(e.format(False, e, mac))
            sig.error.emit(e.format(mac))
            return False, None

    # my exception, ex: no MAT.cfg file
    except AppBLEException as ex:
        e = 'error at {}, will retry'.format(ex)
        sig.logger_post.emit(False, e, mac)
        sig.error.emit('error: {}'.format(e))
        return False, None

    # such as None.command()
    except AttributeError as ae:
        sig.error.emit('error: {}'.format(ae))
        return False, None


class AppBLEException(Exception):
    pass
