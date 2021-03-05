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
    check_local_file_integrity, is_float
)
from ddh.threads.utils_gps_quectel import utils_gps_get_one_lat_lon_dt
from mat.logger_controller import (
    RWS_CMD,
    SWS_CMD, STATUS_CMD
)
from mat.logger_controller_ble import ERR_MAT_ANS
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


def _logger_get_files(lc, sig, folder, files):
    mac, num_to_get, got = lc.per.addr, 0, 0
    name_n_size, b_total = {}, 0

    # filter we'll get, omit locally existing ones
    for each in files.items():
        name, size = each[0], int(each[1])

        if size == 0:
            _show('not downloading {}, size 0'.format(name), sig)
            continue

        if not check_local_file_exists(name, size, folder):
            name_n_size[name] = size
            num_to_get += 1
            b_total += size

    # statistics
    b_left = b_total
    _show('{} has {} files for us'.format(mac, num_to_get), sig)

    # download files one by one
    label = 1
    for name, size in name_n_size.items():
        mm = ((b_left // 5000) // 60) + 1
        b_left -= size
        _show('get {}, {} B'.format(name, size), sig)
        sig.file_pre.emit(name, b_total, label, num_to_get, mm)
        label += 1

        # x-modem download
        s_t = time.time()
        if not lc.get_file(name, folder, size, sig.dl_step):
            _error('can\'t get {}, size {}'.format(name, size))
            return False
        emit_status(sig, 'BLE: got {}'.format(name))

        # check file CRC
        crc = lc.command('CRC', name)
        if check_local_file_integrity(name, folder, crc):
            _error('can\'t get {}, size {}'.format(name, size))
            return False

        # show statistics
        got += 1
        speed = size / (time.time() - s_t)
        sig.file_post.emit(speed)

    # logger was downloaded ok
    _ = 'almost done, '
    if got > 0:
        s = 'got {} file(s)'.format(got)
    elif got == 0:
        s = 'no files to get'
    else:
        s = 'already had all files'
    s = '{}\n{}'.format(_, s)
    sig.logger_post.emit(True, s, mac)

    # success condition
    return num_to_get == got


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


def _logger_re_setup(lc, sig):
    """ get logger's MAT.cfg, formats mem, re-sends MAT.cfg """

    size, rv = 0, _dir_cfg(lc, sig)
    try:
        size = rv['MAT.cfg']
    except (KeyError, TypeError):
        _die('no MAT.cfg within logger to re-setup')
    if not size:
        _die('no MAT.cfg size')

    # download MAT.cfg
    dff = ctx.app_dl_folder
    _show('getting MAT.cfg...', sig)
    if not lc.get_file('MAT.cfg', dff, size, None):
        _die('error downloading MAT.cfg')
    _show('got MAT.cfg', sig)

    # ensure MAT.cfg suitable for CFG command
    try:
        with open(pathlib.Path(dff / 'MAT.cfg')) as f:
            cfg_dict = json.load(f)
            if not cfg_dict:
                _die('no MAT.cfg dict')
    except FileNotFoundError:
        _die('cannot load downloaded MAT.cfg')
    except JSONDecodeError:
        _die('cannot decode downloaded MAT.cfg')

    # format the logger
    rv = lc.command('FRM')
    _ok_or_die([b'FRM', b'00'], rv, sig)

    # re-config the logger
    rv = lc.send_cfg(cfg_dict)
    _ok_or_die([b'CFG', b'00'], rv, sig)


def logger_download(mac, fol, hci_if, sig=None):
    """ downloads logger files and re-setups it """

    try:
        lc = LcBLEFactory.generate(mac)

        with lc(mac, hci_if) as lc:
            # g -> (lat, lon, datetime object)
            g = utils_gps_get_one_lat_lon_dt()
            _logger_sws(lc, sig, g)
            _logger_time_check(lc, sig)

            # DIR logger files and get them
            fol, ls = _logger_ls(lc, fol, sig, pre_rm=False)
            got_all = _logger_get_files(lc, sig, fol, ls)

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
            e = 'logger {} not done yet'
            sig.logger_post.emit(e.format(False, e, mac))
            sig.error.emit(e.format(mac))
            return False, None

    # my exception, ex: no MAT.cfg file
    except AppBLEException as ex:
        e = 'error: {}, will retry'.format(ex)
        sig.logger_post.emit(False, e, mac)
        sig.error.emit(e)
        return False, None

    # bluepy or python exception, ex: None.command()
    except AttributeError as ae:
        sig.error.emit('error: {}'.format(ae))
        return False, None


class AppBLEException(Exception):
    pass
