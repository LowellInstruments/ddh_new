import shelve
import os
import datetime


# careful, Rpi requires 1 packages or it wrongly adds extra 'db' on file_names
# see: stackoverflow 16171833
# $ sudo apt install python3-gdbm


class ColoredMacList:
    def __init__(self, name, sig, color):
        self.db_name = name
        self.sig = sig
        self.color = color

    def delete_all(self):
        try:
            os.remove(self.db_name)
            # print('{}_macs DB erased'.format(self.color))
        except FileNotFoundError as _:
            _e = 'asked to del file {} but not found'
            print(_e.format(self.db_name))

    def macs_dump(self) -> str:
        _s = ''
        with shelve.open(self.db_name) as sh:
            for k, v in sh.items():
                # v: datestamp
                v = int(v - datetime.datetime.now().timestamp())
                _s += '{}: {} seconds left,'.format(k, v)
        return _s

    def macs_add_or_update(self, _mac, _inc):
        _t = datetime.datetime.now().timestamp() + _inc
        with shelve.open(self.db_name) as sh:
            _s = 'SYS: {} to mac_{} list, time increase of {}'
            _s = _s.format(_mac, self.color, _inc)
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
        self.ls = ColoredMacList(name, sig, 'orange')

    def _macs_not_expired(self):
        """ return keys w/ timestamp NOT expired """
        db = shelve.open(self.ls.db_name)
        _bad = []
        _now = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if _now < v:
                _bad.append(k)
        db.close()
        return _bad

    def filter_orange_macs(self, in_macs):
        _o = self._macs_not_expired()
        # remove any not expired ones
        _idx_to_rm = []
        for _ in _o:
            try:
                in_macs.remove(_)
            except ValueError:
                pass
        return in_macs


class BlackMacList:
    """ MACs that went well on download """
    def __init__(self, name, sig):
        self.ls = ColoredMacList(name, sig, 'black')

    def _macs_prune(self):
        """ remove keys with expired timestamp """
        db = shelve.open(self.ls.db_name)
        _expired = []
        _now = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if _now > v:
                _expired.append(k)
        for each in _expired:
            print('SYS: mac {} un-blacked'.format(each))
            del db[each]
        db.close()

    def filter_black_macs(self, in_macs):
        self._macs_prune()
        _bm = self.ls.get_all_macs()
        # return the ones not present in black list
        return [i for i in in_macs if i not in _bm]


def filter_white_macs(wl, in_macs) -> list:
    return [i for i in in_macs if i in wl]


# for purge() buttons
def black_macs_delete_all(name):
    bm = BlackMacList(name, None)
    bm.ls.delete_all()


def bluepy_scan_results_to_strings(sr):
    return [i.addr for i in sr]
