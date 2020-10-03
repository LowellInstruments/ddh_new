import bluepy.btle as ble
import time
import sys
from mat.logger_controller_ble import ble_scan
from settings import ctx
from threads.utils_macs import filter_white_macs, BlackMacList, OrangeMacList
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
        self.black_macs = BlackMacList('.b_m.db', sig)
        self.orange_macs = OrangeMacList('.o_m.db', sig)
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

    def _show_colored_mac_lists(self):
        # black list new or load one
        if not ctx.black_macs_persistent:
            _d = 'SYS: no persistent mac color lists'
            self.black_macs.ls.delete_all(self.sig)
            self.orange_macs.ls.delete_all(self.sig)
            emit_debug(self.sig, _d)
        else:
            _d = 'SYS: loaded persistent black list -> '
            _d += self.black_macs.ls.macs_dump()
            emit_debug(self.sig, _d)
            # _d = 'SYS: loaded persistent orange list -> '
            # _d += self.orange_macs.ls.macs_dump()
            # emit_debug(self.sig, _d)

    def _black_mac(self, mac):
        _fxn = self.black_macs.ls.macs_add_or_update
        _fxn(mac, self.FORGET_S)
        # also remove from _orange, if so!
        self.orange_macs.ls.macs_del_one(mac)

    def _orange_mac(self, mac):
        _fxn = self.orange_macs.ls.macs_add_or_update
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

            # BLE scan: all BLE devices around, no filter
            my_if = 'built-in' if hci_if == 0 else 'external'
            s = 'scanning'
            emit_scan_pre(sig, s)
            near = ble_scan(hci_if)

            # filter by known MAC addresses
            li = filter_white_macs(self.KNOWN_MACS, near)

            # update them and don't query already done ones
            self.black_macs.macs_prune()
            li = self.black_macs.filter_black_macs(li)
            _n = len(li)

            # see how many had errors in past
            _n_o = self.orange_macs.ls.len_macs_list()
            _o = self.orange_macs.ls.get_all_macs()

            # we detect absolutely no logger to do
            if _n + _n_o == 0:
                continue
            s = 'BLE: {} fresh loggers'.format(_n)
            emit_status(sig, s)
            emit_scan_post(sig, _n)
            emit_dl_warning(sig, _o)

            # protect critical zone
            ctx.sem_ble.acquire()

            # downloading stage
            for i, each in enumerate(li):
                mac = each.addr

                try:
                    emit_session_pre(sig, mac, i + 1, _n)
                    emit_status(sig, 'BLE: connecting {}'.format(mac))
                    emit_logger_pre(sig)
                    fol = ctx.dl_files_folder

                    # logger_download() emits all signals
                    done = logger_download(mac, fol, hci_if, sig)
                    self._black_mac(mac) if done else self._orange_mac(mac)

                # not ours, but bluepy exception
                except ble.BTLEException as ex:
                    self._orange_mac(mac)
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
