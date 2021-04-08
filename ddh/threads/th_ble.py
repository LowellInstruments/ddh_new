import os
import pathlib
import shutil

import bluepy.btle as ble
import time
from mat.logger_controller_ble import ble_scan, FAKE_MAC_CC26X2
from ddh.settings import ctx
from ddh.threads.utils import json_get_macs, json_get_forget_time_secs, json_get_hci_if, wait_boot_signal, \
    json_get_forget_time_at_sea_secs, is_float, get_folder_path_from_mac
from ddh.threads.utils_ble import logger_interact
from ddh.threads.utils_gps_quectel import utils_gps_in_land
from ddh.threads.utils_macs import filter_white_macs, bluepy_scan_results_to_macs_string, ColorMacList


TOO_MANY_DL_ERRS_TIME_S = 3600
IGNORE_TIME_S = 60


def _mac_show_color_lists_on_boot(w, ml):

    s = 'SYS: purging orange mac list on boot'
    w.sig_ble.debug.emit(s)
    ol = ml.macs_get_orange()
    for each in ol:
        ml.entry_delete(each)

    # debug hook, may force a brand new mac black list
    if ctx.dbg_hook_purge_mac_blacklist_on_boot:
        s = 'SYS: loaded previous mac_black_list -> {}'
        w.sig_ble.debug.emit(s.format(ml.get_all_entries_as_string()))
        s = 'SYS: forced pre-removing mac_black_list'
        ml.delete_color_mac_file()
        w.sig_ble.debug.emit(s)

    s = 'SYS: loaded current mac_black_list -> {}'
    w.sig_ble.debug.emit(s.format(ml.get_all_entries_as_string()))


def _scan_loggers(w, h, whitelist, ml):

    # scan all BLE devices around, hint: '!' in GUI when USB dongle
    s = '!' if h else ''
    w.sig_ble.scan_pre.emit('scanning{}'.format(s))
    near = ble_scan(h)

    # scan results format -> [strings]
    li = bluepy_scan_results_to_macs_string(near)

    # debug hook, adds at least one logger
    if ctx.dbg_hook_make_dummy_ti_logger_visible:
        li.append(FAKE_MAC_CC26X2)

    # any BLE mac -> DDH known macs
    li = filter_white_macs(whitelist, li)

    # DDH macs -> w/o recently well done ones
    li = ml.macs_filter_not_in_black(li)

    # DDH macs -> w/o too recent bad ones
    li = ml.macs_filter_not_in_orange(li)

    # display number of fresh loggers to be downloaded
    n = len(li)
    if n:
        s = 'BLE: {} fresh loggers'.format(n)
        w.sig_ble.status.emit(s)
    return li


def _download_all_loggers(w, h, macs, ml, ft: tuple):
    """ downloads every BLE logger found """

    # ensure all scanned macs format in lower case
    li = [i.lower() for i in macs]

    # protect critical zone
    ctx.sem_ble.acquire()

    # loop along all loggers
    for i, mac in enumerate(li):

        # debug hook, removes existing logger files before download session
        if ctx.dbg_hook_purge_dl_files_for_this_mac:
            w.sig_ble.debug.emit('BLE: dbg_hook_pre_rm_files {}'.format(mac))
            _pre_rm_path = pathlib.Path(get_folder_path_from_mac(mac))
            shutil.rmtree(str(_pre_rm_path), ignore_errors=True)

        try:
            # this logger session: banner
            fol = ctx.app_dl_folder
            w.sig_ble.session_pre.emit(mac, i + 1, len(li))
            w.sig_ble.status.emit('BLE: connecting {}'.format(mac))
            w.sig_ble.logger_pre.emit()
            done, g = logger_interact(mac, fol, h, w.sig_ble)

            # this logger session: NOT OK, check retries left
            if not done:
                r = ml.retries_get_from_orange_mac(mac)
                r = 1 if not r else r + 1 if r < 5 else 5
                if r == 5:
                    # case lost -> remove from orange list, add to black
                    ml.entry_delete(mac)
                    ml.entry_add_or_update(mac, TOO_MANY_DL_ERRS_TIME_S, r, 'black')
                    e = 'BLE: too many errors for {} -> black-list as r = {}'.format(mac, r)
                else:
                    # still hope -> add to orange list
                    ml.entry_add_or_update(mac, IGNORE_TIME_S, r, 'orange')
                    e = 'BLE: error for {} -> orange-list as r = {}'.format(mac, r)
                w.sig_ble.error.emit(e.format(mac))
                continue

            # this logger session: OK! set 'forget time sea or land'
            ft_s, ft_sea_s = ft
            lat, lon, _ = g if g else (None,) * 3
            if lat and is_float(lat) and lon and is_float(lon):
                if utils_gps_in_land(lat, lon):
                    t = ft_s
                    s = 'BLE: in-land GPS, blacklist {} w/ {} secs'.format(mac, t)
                else:
                    t = ft_sea_s
                    s = 'BLE: at sea GPS, blacklist {} w/ {} secs'.format(mac, t)
            else:
                t = ft_sea_s
                s = 'BLE: bad GPS signal or off, blacklist {} w/ {} secs'.format(mac, t)

            # un-orange logger (if so) and black-list it
            ml.entry_delete(mac)
            ml.entry_add_or_update(mac, t, 0, 'black')
            w.sig_ble.debug.emit(s)

        except ble.BTLEException as ex:
            # not ours, but bluepy exception
            ml.entry_delete(mac)
            ml.entry_add_or_update(mac, IGNORE_TIME_S, 0, 'orange')
            e = 'BLE: caught exception {} -> orange-list as r = 0'.format(ex)
            w.sig_ble.error.emit(e)

        finally:
            ctx.sem_ble.release()

    # give time for messages to display
    time.sleep(3)


def loop(w, ev_can_i_boot):
    """ BLE loop: scan, download and re-deploy found loggers """

    # this th_ble thread waits to boot
    wait_boot_signal(w, ev_can_i_boot, 'BLE')

    # variables needed
    whitelist = json_get_macs(ctx.app_json_file)
    h = json_get_hci_if(ctx.app_json_file)
    ml = ColorMacList(ctx.db_color_macs, w.sig_ble)
    ft_s = json_get_forget_time_secs(ctx.app_json_file)
    ft_sea_s = json_get_forget_time_at_sea_secs(ctx.app_json_file)
    assert ft_s >= 3600
    assert ft_sea_s >= 900
    _mac_show_color_lists_on_boot(w, ml)

    while 1:
        # user disabled the BLE scan with secret click on BLE
        if not ctx.ble_en:
            w.sig_ble.scan_pre.emit('not scanning')
            time.sleep(3)
            continue

        try:
            # >>> scan stage
            macs = _scan_loggers(w, h, whitelist, ml)
            if not macs:
                continue

            # >>> download stage
            _download_all_loggers(w, h, macs, ml, (ft_s, ft_sea_s))

            # >>> report stage w/ download errors, may NOT be any
            ol = ml.macs_get_orange()
            w.sig_ble.logger_dl_warning.emit(ol)

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
