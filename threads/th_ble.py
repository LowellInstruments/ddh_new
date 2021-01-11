import os
import bluepy.btle as ble
import time
from mat.logger_controller_ble import ble_scan
from settings import ctx
from threads.utils import json_get_macs, json_get_forget_time_secs, json_get_hci_if, wait_boot_signal, \
    json_get_forget_time_at_sea_secs
from threads.utils_ble import logger_download
from threads.utils_gps_internal import gps_in_land
from threads.utils_macs import filter_white_macs, BlackMacList, OrangeMacList, bluepy_scan_results_to_strings


IGNORE_TIME_S = 60


def _mac_to_black_list(mb, mo, mac, t):
    mb.ls.macs_add_or_update(mac, t)
    # could be a currently orange one, or not
    mo.ls.macs_del_one(mac)


def _mac_to_orange_list(mo, mac):
    mo.ls.macs_add_or_update(mac, IGNORE_TIME_S)


def _mac_show_color_lists(w, mb, mo):
    if not ctx.macs_lists_persistent:
        # not persistent? remove old lists
        _d = 'SYS: no persistent mac color lists'
        mb.ls.delete_all()
        mo.ls.delete_all()
        w.sig_ble.debug.emit(_d)
    else:
        _d = 'SYS: loaded persistent black list -> '
        _d += mb.ls.macs_dump()
        w.sig_ble.debug.emit(_d)
        _d = 'SYS: loaded persistent orange list -> '
        _d += mo.ls.macs_dump()
        w.sig_ble.debug.emit(_d)
        _d = 'SYS: deleting all orange entries'
        w.sig_ble.debug.emit(_d)
        mo.ls.delete_all()
        # todo: on production, remove this blacklist deletion
        _d = 'SYS: --- warning testing --- deleting all black entries'
        w.sig_ble.debug.emit(_d)
        mb.ls.delete_all()


def _scan_loggers(w, h, whitelist, mb, mo):
    # scan all BLE devices around, '!' when USB dongle
    hci_if = '!' if h else ''
    w.sig_ble.scan_pre.emit('scanning{}'.format(hci_if))
    near = ble_scan(h)

    # scan results format -> [strings]
    li = bluepy_scan_results_to_strings(near)

    # any BLE mac -> DDH known macs
    li = filter_white_macs(whitelist, li)

    # DDH macs -> w/o recently well done ones
    li = mb.filter_black_macs(li)

    # DDH macs -> w/o too recent bad ones
    li = mo.filter_orange_macs(li)

    # banner number of fresh loggers to be downloaded now
    n = len(li)
    if n:
        s = 'BLE: {} fresh loggers'.format(n)
        w.sig_ble.status.emit(s)
    return li


def _download_loggers(w, h, macs, mb, mo, ft: tuple):
    li = [i.lower() for i in macs]

    # protect critical zone
    ctx.sem_ble.acquire()

    # downloading files
    for i, mac in enumerate(li):
        try:
            w.sig_ble.session_pre.emit(mac, i + 1, len(li))
            w.sig_ble.status.emit('BLE: connecting {}'.format(mac))
            w.sig_ble.logger_pre.emit()
            fol = ctx.dl_folder

            # get files from logger
            done, g = logger_download(mac, fol, h, w.sig_ble)

            # NOT OK download session, we will retry this logger after 'ignore time'
            if not done:
                _mac_to_orange_list(mo, mac)

                # display how many pending because previous errors
                orange_pending_ones = mo.ls.get_all_macs()
                w.sig_ble.dl_warning.emit(orange_pending_ones)
                continue

            # OK download session, set conditional (land / sea) 'forget time'
            lat, lon, _ = g
            ft_s, ft_sea_s = ft
            t = ft_s if gps_in_land(lat, lon) else ft_sea_s
            _mac_to_black_list(mb, mo, mac, t)


        except ble.BTLEException as ex:
            # not ours, but bluepy exception
            _mac_to_orange_list(mo, mac)
            w.sig_ble.error.emit('BLE: disconnect exc {}'.format(ex))

    # unprotect critical zone, give time to show messages
    ctx.sem_ble.release()
    time.sleep(3)


def loop(w, ev_can_i_boot):
    wait_boot_signal(w, ev_can_i_boot, 'BLE')

    whitelist = json_get_macs(ctx.json_file)
    h = json_get_hci_if(ctx.json_file)
    mb = BlackMacList(ctx.db_blk, w.sig_ble)
    mo = OrangeMacList(ctx.db_ong, w.sig_ble)
    ft_s = json_get_forget_time_secs(ctx.json_file)
    ft_sea_s = json_get_forget_time_at_sea_secs(ctx.json_file)
    assert ft_s >= 3600
    assert ft_sea_s >= 900
    _mac_show_color_lists(w, mb, mo)

    while 1:
        if not ctx.ble_en:
            w.sig_ble.ble_scan_pre('BLE: not scanning')
            time.sleep(3)
            continue

        try:
            # scan stage
            macs = _scan_loggers(w, h, whitelist, mb, mo)
            if not macs:
                continue

            # download stage
            _download_loggers(w, h, macs, mb, mo, (ft_s, ft_sea_s))
        except ble.BTLEManagementError as ex:
            e = 'BLE: big error, wrong HCI or permissions? {}'
            w.sig_ble.error.emit(e.format(ex))
            time.sleep(1)
            os._exit(1)
