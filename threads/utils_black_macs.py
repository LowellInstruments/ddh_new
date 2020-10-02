import shelve
import os
import datetime


class BlackMacList:
    def __init__(self, name):
        self.db_name = name

    def black_macs_prune(self):
        """ remove keys with expired timestamp """
        db = shelve.open(self.db_name)
        _to_rm = []
        _till = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if _till > v:
                _to_rm.append(k)
        for each in _to_rm:
            print('del {} from blacklist'.format(each))
            del db[each]
        db.close()

    def black_macs_add_or_update(self, _mac, _inc):
        _till = datetime.datetime.now().timestamp() + _inc
        with shelve.open(self.db_name) as sh:
            sh[_mac] = _till

    def black_macs_len(self):
        with shelve.open(self.db_name) as sh:
            return len(sh)

    def black_macs_get(self, _mac):
        try:
            with shelve.open(self.db_name) as sh:
                return sh[_mac]
        except KeyError:
            return None

    def black_macs_is_present(self, _mac):
        with shelve.open(self.db_name) as sh:
            return _mac in sh.keys()

    def black_macs_how_many_pending(self, lgs):
        self.black_macs_prune()
        _ = [i.addr for i in lgs if not self.black_macs_is_present(i.addr)]
        return len(_)


def whitelist_filter(wl, scan_results) -> list:
    return [i for i in scan_results if i.addr in wl]


def black_macs_delete_all(name):
    try:
        os.remove(name)
    except FileNotFoundError as fnf:
        # print(fnf)
        pass


def black_macs_dump(name) -> str:
    _s = ''
    with shelve.open(name) as sh:
        for k, v in sh.items():
            _s += '{}: {}, '.format(k, v)
    return _s
