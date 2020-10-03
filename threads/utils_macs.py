import shelve
import os
import datetime

from threads.utils_ble import emit_debug


class ColoredMacList:
    def __init__(self, name, sig, color):
        self.db_name = name
        self.sig = sig
        self.color = color

    def delete_all(self):
        try:
            os.remove(self.db_name)
            _s = '{}_macs DB erased'.format(self.color)
            emit_debug(self.sig, _s)
        except FileNotFoundError as _:
            _e = 'asked to del file {} but not found'
            print(_e)

    def macs_dump(self) -> str:
        _s = ''
        with shelve.open(self.db_name) as sh:
            for k, v in sh.items():
                _s += '{}: {}, '.format(k, v)
        return _s

    def macs_add_or_update(self, _mac, _inc):
        _t = datetime.datetime.now().timestamp() + _inc
        with shelve.open(self.db_name) as sh:
            _s = 'SYS: mac {} oranged'
            _s = _s.format(_mac, self.color)
            emit_debug(self.sig, _s)
            sh[_mac] = _t

    def macs_del_one(self, _mac):
        try:
            with shelve.open(self.db_name) as sh:
                del sh[_mac]
        except KeyError:
            pass

    def len_macs_list(self):
        with shelve.open(self.db_name) as sh:
            return len(sh)

    def get_all_macs(self) -> list:
        with shelve.open(self.db_name) as sh:
            return list(sh.keys())


class OrangeMacList:
    """ MACs that had error on download """
    def __init__(self, name, sig):
        self.ls = ColoredMacList(name, sig, 'orange\'')

    def macs_refresh(self):
        """ return (not remove) keys w/ expired timestamp """
        db = shelve.open(self.ls.db_name)
        _expired = []
        _now = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if _now > v:
                _expired.append(k)
        db.close()
        return _expired


class BlackMacList:
    """ MACs that went well on download """
    def __init__(self, name, sig):
        self.ls = ColoredMacList(name, sig, 'black\'')

    def macs_prune(self):
        """ remove keys with expired timestamp """
        db = shelve.open(self.ls.db_name)
        _expired = []
        _now = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if _now > v:
                _expired.append(k)
        for each in _expired:
            _s = 'SYS: mac {} un-blacked'.format(each)
            emit_debug(self.ls.sig, _s)
            del db[each]
        db.close()

    def filter_black_macs(self, s_r):
        """ s_r: bluepy scan results """
        _m = self.ls.get_all_macs()
        # return the ones not present in black list
        return [i for i in s_r if i.addr not in _m]


def filter_white_macs(wl, scan_results) -> list:
    return [i for i in scan_results if i.addr in wl]


def scan_results_to_macs(sr) -> list:
    return [_.addr for _ in sr]


# for purge() buttons
def black_macs_delete_all(name):
    bm = BlackMacList(name, None)
    bm.ls.delete_all()
