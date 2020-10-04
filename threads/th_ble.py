import bluepy.btle as ble
import time
import sys
from mat.logger_controller_ble import ble_scan
from settings import ctx
from threads.utils_macs import filter_white_macs, BlackMacList, OrangeMacList, bluepy_scan_results_to_strings
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

    # really boot BLE thread
    ThBLE(sig, *args)


class ThBLE:
    def __init__(self, sig, forget_s, ignore_s, known_macs, hci_if):
        self.sig = sig
        self.hci_if = hci_if
        self.macs_black = BlackMacList(ctx.db_blk, sig)
        self.macs_orange = OrangeMacList(ctx.db_ong, sig)
        self.FORGET_S = forget_s
        self.IGNORE_S = ignore_s
        self.KNOWN_MACS = [i.lower() for i in known_macs]

        # main BLE loop: scan and download
        while 1:
            try:
                self._loop(self.sig, self.hci_if)
            except ble.BTLEManagementError as ex:
                # leave this app, big SYS BLE error
                e = 'BLE: big error, wrong HCI or permissions?'
                emit_error(sig, e)
                print(ex)
                time.sleep(1)
                sys.exit(1)

    def _show_colored_mac_lists(self):
        if not ctx.black_macs_persistent:
            # not persistent? remove old lists
            _d = 'SYS: no persistent mac color lists'
            self.macs_black.ls.delete_all(self.sig)
            self.macs_orange.ls.delete_all(self.sig)
            emit_debug(self.sig, _d)
        else:
            _d = 'SYS: loaded persistent black list -> '
            _d += self.macs_black.ls.macs_dump()
            emit_debug(self.sig, _d)
            _d = 'SYS: loaded persistent orange list -> '
            _d += self.macs_orange.ls.macs_dump()
            emit_debug(self.sig, _d)

    def _to_black(self, mac):
        _fxn = self.macs_black.ls.macs_add_or_update
        _fxn(mac, self.FORGET_S)
        # could be a previously orange one, or not
        self.macs_orange.ls.macs_del_one(mac)

    def _to_orange(self, mac):
        _fxn = self.macs_orange.ls.macs_add_or_update
        _fxn(mac, self.IGNORE_S)

    def _loop(self, sig, hci_if):
        emit_status(sig, 'BLE: thread boot')
        self._show_colored_mac_lists()

        # BLE loop
        while 1:
            if not ctx.ble_en:
                emit_scan_pre(sig, 'not scanning')
                time.sleep(3)
                continue

            # wireless scan: all BLE devices around, no filter
            _iface = 'external' if hci_if else 'internal'
            s = 'scanning'
            emit_scan_pre(sig, s)
            near = ble_scan(hci_if)

            # scan results format -> [strings]
            li = bluepy_scan_results_to_strings(near)

            # any BLE mac -> DDH known macs
            li = filter_white_macs(self.KNOWN_MACS, li)

            # DDH macs -> w/o recently well done ones
            li = self.macs_black.filter_black_macs(li)

            # DDH macs -> w/o too recent bad ones
            li = self.macs_orange.filter_orange_macs(li)

            # how many loggers we have to do now
            n = len(li)

            # none to download, great
            if n == 0:
                emit_dl_warning(sig, None)
                continue
            s = 'BLE: {} fresh loggers'.format(n)
            emit_status(sig, s)
            emit_scan_post(sig, n)

            # remind we may not be done with some
            _o = self.macs_orange.macs_orange_pick()
            emit_dl_warning(sig, _o)

            # protect critical zone
            ctx.sem_ble.acquire()

            # downloading stage
            for i, each in enumerate(li):
                mac = each.addr

                try:
                    emit_session_pre(sig, mac, i + 1, n)
                    emit_status(sig, 'BLE: connecting {}'.format(mac))
                    emit_logger_pre(sig)
                    fol = ctx.dl_files_folder

                    # logger_download() emits all signals
                    done = logger_download(mac, fol, hci_if, sig)
                    self._to_black(mac) if done else self._to_orange(mac)

                # not ours, but bluepy exception
                except ble.BTLEException as ex:
                    # add to orange ones
                    self._to_orange(mac)
                    ex = str(ex.message)
                    e = 'BLE: exception {}'.format(ex)
                    emit_error(sig, e)
                    e = 'DL error, retrying in {} s'
                    e = e.format(self.IGNORE_S)
                    emit_error(sig, e)
                    e = 'some error\nretrying in 1 min'
                    emit_logger_post(sig, False, e, mac)

            # unprotect critical zone
            ctx.sem_ble.release()

            # gives time to display messages
            time.sleep(3)
