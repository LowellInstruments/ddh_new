import bluepy.btle as ble
import time
import os
from mat.logger_controller_ble import ble_scan
from context import ctx
from threads.utils_ble import (
    logger_download,
    emit_scan_pre,
    emit_scan_post,
    emit_status,
    emit_error,
    emit_error_gui, emit_logger_pre, emit_session_pre, emit_logger_plot_req)


def fxn(sig, args):
    ThBLE(sig, *args)


class ThBLE:
    def __init__(self, sig, forget_s, ignore_s, known_macs, hci_if):
        ThBLE.__one = self
        self.sig = sig
        self.hci_if = hci_if
        self.blacklist = dict()
        self.FORGET_S = forget_s
        self.IGNORE_S = ignore_s
        self.KNOWN_MACS = [i.lower() for i in known_macs]

        # main BLE behavior: scan and download
        try:
            self._loop(self.sig, self.hci_if)
        except ble.BTLEManagementError as ex:
            e = 'BLE: big error, wrong HCI or permissions?'
            emit_error(sig, e)
            print(ex)
            time.sleep(1)
            os._exit(1)

    def _loop(self, sig, hci_if):
        emit_status(sig, 'BLE: thread boot')

        while 1:

            # nothing when BLE disabled
            if not ctx.ble_en:
                emit_scan_pre(sig, 'BLE: stopped')
                time.sleep(1)
                continue

            # un-ignore loggers, if so
            self._blacklist_update()

            # BLE scan filter Lowell Instruments' loggers
            my_if = 'built-in' if hci_if == 0 else 'antenna'
            emit_scan_pre(sig, 'scan: {}'.format(my_if))
            near = ble_scan(hci_if)
            li = self._whitelist_filter(near)
            emit_scan_post(sig, li)
            n = len(li)

            # useful when debugging
            s = 'BLE: {} known loggers around'.format(n)
            emit_status(sig, s)

            # protect critical zone
            ctx.ble_ongoing = True

            # downloading stage
            for i, each in enumerate(li):
                mac = each.addr
                if self._blacklist_present(mac):
                    continue

                try:
                    emit_session_pre(sig, mac, i + 1, n)
                    emit_status(sig, 'BLE: connecting {}'.format(mac))
                    emit_logger_pre(sig)
                    fol = ctx.dl_files_folder
                    rv = logger_download(mac, fol, hci_if, sig)
                    self._blacklist_add(mac, rv)
                except ble.BTLEException as ex:
                    self._blacklist_add(mac, False)
                    ex = str(ex.message)
                    e = 'BLE: exception {}'.format(ex)
                    emit_error(sig, e)
                    e = 'DL error, retrying in {} s'
                    e = e.format(self.IGNORE_S)
                    emit_error_gui(sig, e)
                    emit_error(sig, e)
                    print(ex)

            # unprotect critical zone
            ctx.ble_ongoing = False

    def _blacklist_update(self):
        for key, value in list(self.blacklist.items()):
            if time.time() > value:
                self.blacklist.pop(key)
            # useful when debugging
            # else:
            #     yet = value - time.time()
            #     t = 'BLE: omit {} for {:.2f} s'.format(key, yet)
            #     emit_status(self.sig, t)

    def _blacklist_present(self, a):
        return a in self.blacklist

    def _blacklist_add(self, mac, went_ok):
        # FORGET_S: went things go well, IGNORE_s: not
        t = self.FORGET_S if went_ok else self.IGNORE_S
        s = 'BLE: will omit {} for {} s'.format(mac, t)
        emit_status(self.sig, s)
        d = {mac: time.time() + t}
        self.blacklist.update(d)

    def _blacklist_show(self):
        for i, t in self.blacklist.items():
            print('{}, {}s'.format(i, t))

    def _whitelist_filter(self, sr):
        whitelist = self.KNOWN_MACS
        return [i for i in sr if i.addr in whitelist]
