import bluepy.btle as ble
import time
import sys
from db.db_blk import DBBlk
from mat.logger_controller_ble import ble_scan
from settings import ctx
from threads.utils_ble import (
    logger_download,
    emit_scan_pre,
    emit_status,
    emit_error,
    emit_logger_pre, emit_session_pre, emit_logger_post, emit_debug, emit_scan_post)


def fxn(sig, args):
    while not ctx.boot_time:
        emit_status(sig, 'BLE: wait GPS boot time')
        time.sleep(5)
        continue

    ThBLE(sig, *args)


class ThBLE:
    def __init__(self, sig, forget_s, ignore_s, known_macs, hci_if):
        self.sig = sig
        self.hci_if = hci_if
        self.blacklist_dict = dict()
        if ctx.ble_blacklist_persistent:
            self.blacklist_dict = self._blacklist_from_db()
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

        while 1:
            if not ctx.ble_en:
                emit_scan_pre(sig, 'not scanning')
                time.sleep(3)
                continue

            # un-ignore loggers, if so
            self._blacklist_prune()

            # BLE scan: all BLE devices around, no filter
            my_if = 'built-in' if hci_if == 0 else 'external'
            s = 'scanning'
            emit_scan_pre(sig, s)
            near = ble_scan(hci_if)

            # filter by known MAC addresses
            li = self._whitelist_filter(near)

            # filter by too recent ones
            n = self._loggers_left_to_do(li)

            # we detect absolutely no logger to do
            if n == 0:
                continue
            s = 'BLE: {} loggers detected'.format(n)
            emit_status(sig, s)
            emit_scan_post(sig, n)

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

                    # logger_download() emits all signals
                    done = logger_download(mac, fol, hci_if, sig)
                    self._blacklist_add(mac, done)

                # not ours, but python BLE lib exception
                except ble.BTLEException as ex:
                    self._blacklist_add(mac, False)
                    ex = str(ex.message)
                    print(ex)
                    e = 'BLE: exception {}'.format(ex)
                    emit_error(sig, e)
                    e = 'DL error, retrying in {} s'
                    e = e.format(self.IGNORE_S)
                    emit_error(sig, e)
                    e = 'some error\nretrying in 1 minute'
                    emit_logger_post(sig, False, e, mac)

            # unprotect critical zone
            ctx.ble_ongoing = False

            # gives time to display messages
            time.sleep(3)

    def _blacklist_from_db(self):
        # called in ThBLE constructor
        bl = dict()
        db = DBBlk(ctx.db_blk)
        r = db.list_all_records()
        for each in r:
            _ = {each[1]: each[2]}
            bl.update(_)
            s = 'BLE: bl <- db entry {}'
            emit_debug(self.sig, s.format(bl))
        return bl

    def _blacklist_to_db(self):
        db = DBBlk(ctx.db_blk)
        db.delete_all_records()
        for _ in self.blacklist_dict.items():
            db.add_record(_[0], _[1])
            s = 'BLE: bl entry -> db {}'
            emit_debug(self.sig, s.format(_))

    def _blacklist_prune(self):
        some_blacklist_update = False
        for key, value in list(self.blacklist_dict.items()):
            if time.time() > float(value):
                some_blacklist_update = True
                self.blacklist_dict.pop(key)
            # useful when debugging
            # else:
            #     yet = value - time.time()
            #     t = 'BLE: omit {} for {:.2f} s'.format(key, yet)
            #     emit_status(self.sig, t)

        if some_blacklist_update and ctx.ble_blacklist_persistent:
            self._blacklist_to_db()

    def _blacklist_present(self, a):
        return a in self.blacklist_dict

    def _blacklist_add(self, mac, went_ok):
        t = self.FORGET_S if went_ok else self.IGNORE_S
        s = 'BLE: will omit {} for {} s'.format(mac, t)
        emit_status(self.sig, s)
        d = {mac: time.time() + t}
        self.blacklist_dict.update(d)
        if ctx.ble_blacklist_persistent:
            self._blacklist_to_db()

    def _blacklist_show(self):
        for i, t in self.blacklist_dict.items():
            print('{}, {}s'.format(i, t))

    def _whitelist_filter(self, sr):
        whitelist = self.KNOWN_MACS
        return [i for i in sr if i.addr in whitelist]

    def _loggers_left_to_do(self, lgs):
        """ counts new loggers and blacklisted about to expire """
        to_do = 0
        for i in lgs:
            try:
                t = float(self.blacklist_dict[i.addr])
                if t <= self.IGNORE_S:
                    to_do += 1
            except KeyError:
                to_do += 1
                pass
        return to_do
