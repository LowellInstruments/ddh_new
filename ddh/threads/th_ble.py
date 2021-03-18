import os
import pathlib
import shutil

import bluepy.btle as ble
import time
from mat.logger_controller_ble import ble_scan, FAKE_MAC_CC26X2
from ddh.settings import ctx
from ddh.threads.utils import json_get_macs, json_get_forget_time_secs, json_get_hci_if, wait_boot_signal, \
    json_get_forget_time_at_sea_secs, is_float, get_folder_path_from_mac
from ddh.threads.utils_ble import logger_download
from ddh.threads.utils_gps_quectel import utils_gps_in_land
from ddh.threads.utils_macs import filter_white_macs, BlackMacList, OrangeMacList, bluepy_scan_results_to_strings


IGNORE_TIME_S = 60


def _mac_to_black_list(mb, mo, mac, t):

    mb.ls.macs_add_or_update(mac, t)
    # could be a currently orange one, or not
    mo.ls.macs_del_one(mac)


def _mac_to_orange_list(mo, mac):

    mo.ls.macs_add_or_update(mac, IGNORE_TIME_S)


def _mac_show_color_lists_on_boot(w, mb, mo):

    _d = 'SYS: purging mac_orange_list on boot'
    w.sig_ble.debug.emit(_d)
    mo.ls.delete_all()

    # debug hook, forces a brand new mac black list
    if ctx.macs_blacklist_pre_rm:
        _d = 'SYS: forced pre-removing mac_black_list'
        mb.ls.delete_all()
        w.sig_ble.debug.emit(_d)

    _d = 'SYS: loaded mac_black_list -> '
    _d += mb.ls.macs_dump()
    w.sig_ble.debug.emit(_d)
    _d = 'SYS: loaded mac_orange_list -> '
    _d += mo.ls.macs_dump()
    w.sig_ble.debug.emit(_d)


def _scan_loggers(w, h, whitelist, mb, mo):

    # scan all BLE devices around, hint: '!' when USB dongle
    s = '!' if h else ''
    w.sig_ble.scan_pre.emit('scanning{}'.format(s))
    near = ble_scan(h)

    # scan results format -> [strings]
    li = bluepy_scan_results_to_strings(near)

    # debug hook, adds at least one logger
    if ctx.dummy_ti_logger:
        li.append(FAKE_MAC_CC26X2)

    # any BLE mac -> DDH known macs
    li = filter_white_macs(whitelist, li)

    # DDH macs -> w/o recently well done ones
    li = mb.filter_black_macs(li)

    # DDH macs -> w/o too recent bad ones
    li = mo.filter_orange_macs(li)

    # banner number of fresh loggers to be downloaded
    n = len(li)
    if n:
        s = 'BLE: {} fresh loggers'.format(n)
        w.sig_ble.status.emit(s)
    return li


def _download_loggers(w, h, macs, mb, mo, ft: tuple):
    """ downloads every BLE logger found """

    # ensure all scanned macs format in lower case
    li = [i.lower() for i in macs]

    # protect critical zone
    ctx.sem_ble.acquire()

    # downloading files
    for i, mac in enumerate(li):

        # debug hook, removes existing logger files before download session
        if ctx.pre_rm_files:
            s = 'BLE: pre_rm_files for {}'.format(mac)
            w.sig_ble.debug.emit(s)
            _pre_rm_path = pathlib.Path(get_folder_path_from_mac(mac))
            shutil.rmtree(str(_pre_rm_path), ignore_errors=True)

        try:
            # start a download session for ONE logger
            w.sig_ble.session_pre.emit(mac, i + 1, len(li))
            w.sig_ble.status.emit('BLE: connecting {}'.format(mac))
            w.sig_ble.logger_pre.emit()
            fol = ctx.app_dl_folder

            # get files from the logger
            done, g = logger_download(mac, fol, h, w.sig_ble)

            # update GUI with logger pending warnings, if any
            orange_pending_ones = mo.ls.get_all_macs()
            w.sig_ble.dl_warning.emit(orange_pending_ones)

            # NOT OK download session, ignore logger for 'ignore time'
            if not done:
                e = 'BLE: download process did not finish for {}'
                w.sig_ble.error.emit(e.format(mac))
                _mac_to_orange_list(mo, mac)
                continue

            # OK download session, set 'forget time_sea or land'
            ft_s, ft_sea_s = ft
            lat, lon, _ = g if g else (None,) * 3
            if lat and is_float(lat) and lon and is_float(lon):
                if utils_gps_in_land(lat, lon):
                    t = ft_s
                    s = 'BLE: in-land, blacklist {} w/ {} secs'.format(mac, t)
                else:
                    t = ft_sea_s
                    s = 'BLE: at sea, blacklist {} w/ {} secs'.format(mac, t)
            else:
                t = ft_sea_s
                s = 'BLE: no idea about sea or in-land, blacklist {} w/ {} secs'.format(mac, t)

            w.sig_ble.debug.emit(s)
            _mac_to_black_list(mb, mo, mac, t)

        except ble.BTLEException as ex:
            # not ours, but bluepy exception
            _mac_to_orange_list(mo, mac)
            w.sig_ble.error.emit('BLE: disconnect exc {}'.format(ex))

        finally:
            # unprotect critical zone
            ctx.sem_ble.release()

    # give time to show messages
    time.sleep(3)


def loop(w, ev_can_i_boot):
    """ BLE loop: scan, download and re-deploy found loggers """

    wait_boot_signal(w, ev_can_i_boot, 'BLE')

    whitelist = json_get_macs(ctx.app_json_file)
    h = json_get_hci_if(ctx.app_json_file)
    mb = BlackMacList(ctx.db_blk, w.sig_ble)
    mo = OrangeMacList(ctx.db_ong, w.sig_ble)
    ft_s = json_get_forget_time_secs(ctx.app_json_file)
    ft_sea_s = json_get_forget_time_at_sea_secs(ctx.app_json_file)
    assert ft_s >= 3600
    assert ft_sea_s >= 900
    _mac_show_color_lists_on_boot(w, mb, mo)

    while 1:
        if not ctx.ble_en:
            w.sig_ble.scan_pre.emit('not scanning')
            time.sleep(3)
            continue

        try:
            # >>> scan stage
            macs = _scan_loggers(w, h, whitelist, mb, mo)
            if not macs:
                continue

            # >>> download stage
            _download_loggers(w, h, macs, mb, mo, (ft_s, ft_sea_s))

        except ble.BTLEManagementError as ex:
            e = 'BLE: big error, wrong HCI or permissions? {}'
            w.sig_ble.error.emit(e.format(ex))
            time.sleep(1)
            os._exit(1)

        except ble.BTLEDisconnectError as ex:
            e = 'BLE: weird bluepy error, permissions? {}'
            w.sig_ble.error.emit(e.format(ex))
            time.sleep(1)
            os._exit(1)
