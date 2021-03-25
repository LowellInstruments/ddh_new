import shelve
import os
import datetime


# careful: Rpi requires 1 apt-get or it wrongly adds extra 'db' on file_names
# see: stackoverflow 16171833
# $ sudo apt install python3-gdbm


class ColorMacList:

    def __init__(self, name, sig):
        self.db_name = name
        self.sig = sig

    def delete_color_mac_file(self):
        """ removes database file """

        try:
            os.remove(self.db_name)
            return 0
        except FileNotFoundError as _:
            _e = 'asked to del database color_mac file {} but not found'
            print(_e.format(self.db_name))
            return 1

    def get_all_entries_as_string(self) -> str:
        """ show entries in database {mac: (t, retries, color)} """

        s = ''
        with shelve.open(self.db_name) as sh:
            for k, v in sh.items():
                # v: (datestamp, retries, color)
                t = int(v[0] - datetime.datetime.now().timestamp())
                _ = '{}: {} seconds left, retries {}, color {} / '
                s += _.format(k, t, v[1], v[2])
        return s

    def get_all_orange_entries_as_string(self) -> str:
        """ show entries in database {mac: (t, retries, color)} """

        s = ''
        with shelve.open(self.db_name) as sh:
            for k, v in sh.items():
                if v[2] == 'orange':
                    # v: (datestamp, retries, color)
                    t = int(v[0] - datetime.datetime.now().timestamp())
                    _ = '{}: {} seconds left, retries {}, color {} / '
                    s += _.format(k, t, v[1], v[2])
        return s

    def entry_add_or_update(self, mac, inc, retries, color):
        """ adds or refreshes time of an entry in a mac database """

        assert color in ('black', 'orange')
        assert retries <= 5

        t = datetime.datetime.now().timestamp() + inc
        with shelve.open(self.db_name) as sh:
            sh[mac] = (t, retries, color)

    def entry_delete(self, mac):
        """ removes one entry of database """

        try:
            with shelve.open(self.db_name) as sh:
                del sh[mac]
        except KeyError:
            pass

    def entry_get(self, mac):
        try:
            with shelve.open(self.db_name) as sh:
                return sh[mac]
        except KeyError:
            return None

    def entries_get_all_orange(self) -> dict:
        """ return orange entries """

        db = shelve.open(self.db_name)
        rv = {k: v for k,v in db.items() if v[2] == 'orange'}
        db.close()
        return rv

    def mac_list_len(self):
        with shelve.open(self.db_name) as sh:
            return len(sh)

    def macs_get_all(self) -> list:
        """ returns list of existing macs in a mac database """

        with shelve.open(self.db_name) as sh:
            return list(sh.keys())

    def macs_get_orange_not_expired(self) -> list:
        """ return keys (macs) w/ timestamp NOT expired """

        rv = []
        db = shelve.open(self.db_name)
        _now = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if _now < v[0] and v[2] == 'orange':
                rv.append(k)
        db.close()
        return rv

    def macs_get_orange(self) -> list:
        """ return all orange keys (macs) """

        rv = []
        db = shelve.open(self.db_name)
        _now = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if v[2] == 'orange':
                rv.append(k)
        db.close()
        return rv

    def macs_get_black(self) -> list:
        """ return keys (macs) in black list """

        db = shelve.open(self.db_name)
        rv = []
        for k, v in db.items():
            if v[2] == 'black':
                rv.append(k)
        db.close()
        return rv

    def retries_get_from_orange_mac(self, mac) -> list:
        om = self.entries_get_all_orange()
        try:
            return om[mac][1]
        except KeyError:
            return None

    def macs_filter_not_in_orange(self, in_macs):
        """ return 'in_macs' entries NOT PRESENT in mac_orange_list"""

        o = self.macs_get_orange_not_expired()
        return [i for i in in_macs if i not in o]

    def macs_filter_not_in_black(self, in_macs):
        """ prune() black mac list, return 'in_macs' entries NOT PRESENT in it """

        self.entries_prune_black()
        b = self.macs_get_black()
        return [i for i in in_macs if i not in b]

    def entries_prune_black(self):
        """ remove black macs w/ expired timestamp """

        db = shelve.open(self.db_name)
        _expired = []
        _now = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if _now > v[0] and v[2] == 'black':
                _expired.append(k)
        for each in _expired:
            print('SYS: mac {} un-blacked'.format(each))
            del db[each]
        db.close()


def filter_white_macs(wl, in_macs) -> list:
    return [i for i in in_macs if i in wl]


# for secret EDIT tab purge() buttons
def delete_color_mac_file(name):
    ml = ColorMacList(name, None)
    ml.delete_color_mac_file()


def bluepy_scan_results_to_macs_string(sr):
    return [i.addr for i in sr]
