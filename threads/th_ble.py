import bluepy.btle as ble
import time
import sys
from mat.logger_controller_ble import ble_scan
from settings import ctx
from threads.utils import json_mac_dns
from threads.utils_macs_black import whitelist_filter, BlackMacList, black_macs_delete_all, black_macs_dump
from threads.utils_ble import (
    logger_download,
    emit_scan_pre,
    emit_status,
    emit_error,
    emit_logger_pre, emit_session_pre, emit_logger_post, emit_debug, emit_scan_post, emit_dl_warning)


def fxn(sig, args):
    while not ctx.boot_time:
        emit_status(sig, 'BLE: wait GPS boot time')
        time.sleep(5)

    ThBLE(sig, *args)


class ThBLE:
    def __init__(self, sig, forget_s, ignore_s, known_macs, hci_if):
        self.sig = sig
        self.hci_if = hci_if
        self.black_macs = None
        self.FORGET_S = forget_s
        self.IGNORE_S = ignore_s
        self.KNOWN_MACS = [i.lower() for i in known_macs]

        # main BLE behavior: scan and download
        while 1:
            try:
                self._loop(self.sig, self.hci_if)
            except ble.BTLEManagementError as ex:
                e = 'BLE: big error, wrong HCI or permissions?'
                emit_error(sig, e)
                print(ex)
                time.sleep(1)
                sys.exit(1)

    def _loop(self, sig, hci_if):
        emit_status(sig, 'BLE: thread boot')

        # black list new or load one
        if not ctx.black_macs_persistent:
            _d = 'SYS: no persistent blacklist'
            black_macs_delete_all(ctx.db_blk)
        else:
            _d = 'SYS: loaded persistent blacklist -> '
            _d += black_macs_dump(ctx.db_blk)
        emit_debug(sig, _d)

        # BLE loop
        while 1:
            if not ctx.ble_en:
                emit_scan_pre(sig, 'not scanning')
                time.sleep(3)
                continue

            # to manage black-listed macs
            bm = BlackMacList(ctx.db_blk, sig)

            # un-ignore loggers, if so
            bm.black_macs_prune()

            # BLE scan: all BLE devices around, no filter
            my_if = 'built-in' if hci_if == 0 else 'external'
            s = 'scanning'
            emit_scan_pre(sig, s)
            near = ble_scan(hci_if)

            # filter by known MAC addresses
            li = whitelist_filter(self.KNOWN_MACS, near)

            # filter by too recent ones
            n = bm.black_macs_how_many_pending(li)

            # we detect absolutely no logger to do
            if n == 0:
                continue
            s = 'BLE: {} loggers detected'.format(n)
            emit_status(sig, s)
            emit_scan_post(sig, n)

            # protect critical zone
            ctx.sem_ble.acquire()

            # downloading stage
            for i, each in enumerate(li):
                mac = each.addr
                if bm.black_macs_is_present(mac):
                    continue

                try:
                    emit_session_pre(sig, mac, i + 1, n)
                    emit_status(sig, 'BLE: connecting {}'.format(mac))
                    emit_logger_pre(sig)
                    fol = ctx.dl_files_folder

                    # logger_download() emits all signals
                    done = logger_download(mac, fol, hci_if, sig)
                    _t = self.FORGET_S if done else self.IGNORE_S
                    bm.black_macs_add_or_update(mac, _t)

                # not ours, but python BLE lib exception
                except ble.BTLEException as ex:
                    bm.black_macs_add_or_update(mac, self.IGNORE_S)
                    emit_dl_warning(sig, mac)
                    ex = str(ex.message)
                    e = 'BLE: exception {}'.format(ex)
                    emit_error(sig, e)
                    e = 'DL error, retrying in {} s'
                    e = e.format(self.IGNORE_S)
                    emit_error(sig, e)
                    e = 'some error\nretrying in 1 minute'
                    emit_logger_post(sig, False, e, mac)

            # unprotect critical zone
            ctx.sem_ble.release()

            # gives time to display messages
            time.sleep(3)
