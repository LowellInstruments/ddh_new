import os
import bluepy.btle as ble
import time
from mat.logger_controller_ble import ble_scan
from settings import ctx
from threads.utils import json_get_macs, json_get_forget_time_secs, json_get_hci_if
from threads.utils_ble import logger_download
from threads.utils_macs import filter_white_macs, BlackMacList, OrangeMacList, bluepy_scan_results_to_strings


IGNORE_TIME_S = 60


def _to_black(mb, mo, mac, t):
    mb.ls.macs_add_or_update(mac, t)
    # could be a previously orange one, or not
    mo.ls.macs_del_one(mac)


def _to_orange(mo, mac):
    mo.ls.macs_add_or_update(mac, IGNORE_TIME_S)


def _show_colored_mac_lists(w, mb, mo):
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


def _scan_loggers(w, h, whitelist, mb, mo):
    # scan all BLE devices around
    hci_if = 'external' if h else 'internal'
    w.sig_ble.scan_pre.emit('scanning {}'.format(hci_if))
    near = ble_scan(h)

    # scan results format -> [strings]
    li = bluepy_scan_results_to_strings(near)

    # any BLE mac -> DDH known macs
    li = filter_white_macs(whitelist, li)

    # DDH macs -> w/o recently well done ones
    li = mb.filter_black_macs(li)

    # DDH macs -> w/o too recent bad ones
    li = mo.filter_orange_macs(li)

    # know how many pending because previous errors
    o_p = mo.ls.get_all_macs()
    w.sig_ble.dl_warning.emit(o_p)

    # banner warning left as pending
    _o = mo.ls.get_all_macs()
    w.sig_ble.dl_warning.emit(_o)

    # banner number of loggers to be done
    s = 'BLE: {} fresh loggers'.format(len(li))
    w.sig_ble.status.emit(s)
    w.sig_ble.scan_post.emit(s)
    return li


def _download_loggers(w, h, macs, mb, mo, ft_s):
    li = [i.lower() for i in macs]

    # protect critical zone
    ctx.sem_ble.acquire()

    # downloading stage
    for i, mac in enumerate(li):
        try:
            w.sig_ble.session_pre.emit(mac, i + 1, len(li))
            w.sig_ble.status.emit('BLE: connecting {}'.format(mac))
            w.sig_ble.logger_pre.emit()
            fol = ctx.dl_folder
            done = logger_download(mac, fol, h, w.sig_ble)
            _to_black(mb, mo, mac, ft_s) if done else _to_orange(mo, mac)

        except ble.BTLEException as ex:
            # not ours, but bluepy exception
            _to_orange(mo, mac)
            w.sig_ble.error.emit('BLE: disconnect exc {}'.format(ex))
            w.sig_ble.logger_post.emit('BLE: retrying in {} seconds'.format(IGNORE_TIME_S))

    # unprotect critical zone, give time to show messages
    ctx.sem_ble.release()
    time.sleep(3)


def loop(w):
    w.sig_ble.status.emit('SYS: BLE thread started')
    whitelist = json_get_macs(ctx.json_file)
    h = json_get_hci_if(ctx.json_file)
    mb = BlackMacList(ctx.db_blk, w.sig_ble)
    mo = OrangeMacList(ctx.db_ong, w.sig_ble)
    ft_s = json_get_forget_time_secs(ctx.json_file)
    assert ft_s >= 3600
    _show_colored_mac_lists(w, mb, mo)

    while 1:
        if not ctx.ble_en:
            w.sig_ble.ble_scan_pre('BLE: not scanning')
            time.sleep(3)
            continue

        try:
            macs = _scan_loggers(w, h, whitelist, mb, mo)
            if not macs:
                continue
            _download_loggers(w, h, macs, mb, mo, ft_s)
        except ble.BTLEManagementError as ex:
            e = 'BLE: big error, wrong HCI or permissions? {}'
            w.sig_ble.error.emit(e.format(ex))
            time.sleep(1)
            os._exit(1)
