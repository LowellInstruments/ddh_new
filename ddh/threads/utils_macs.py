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

    def mac_list_delete_file(self):
        """ removes database file """

        try:
            os.remove(self.db_name)
            return 0
        except FileNotFoundError as _:
            _e = 'asked to del database color_mac file {} but not found'
            print(_e.format(self.db_name))
            return 1

    def mac_list_get_all_entries(self) -> str:
        """ show entries in database {mac: (t, retries, color)} """

        s = ''
        with shelve.open(self.db_name) as sh:
            for k, v in sh.items():
                # v: (datestamp, retries, color)
                t = int(v[0] - datetime.datetime.now().timestamp())
                _ = '{}: {} seconds left, retries {}, color {}'
                s += _.format(k, t, v[1], v[2])
        return s

    def mac_list_add_or_update(self, mac, inc, retries, color):
        """ adds or refreshes time of an entry in a mac database """

        assert color in ('black', 'orange')
        assert retries <= 5

        t = datetime.datetime.now().timestamp() + inc
        with shelve.open(self.db_name) as sh:
            sh[mac] = (t, retries, color)

    def mac_list_del_one(self, mac):
        """ removes one entry of a mac database, orange or black """

        try:
            with shelve.open(self.db_name) as sh:
                del sh[mac]
        except KeyError:
            pass

    def mac_list_get_one(self, mac):
        try:
            with shelve.open(self.db_name) as sh:
                return sh[mac]
        except KeyError:
            return None

    def mac_list_len(self):
        with shelve.open(self.db_name) as sh:
            return len(sh)

    def mac_list_get_all_macs(self) -> list:
        """ returns list of existing macs in a mac database """

        with shelve.open(self.db_name) as sh:
            return list(sh.keys())

    def mac_list_get_all_orange_macs_not_expired(self) -> list:
        """ return keys (macs) w/ timestamp NOT expired """

        db = shelve.open(self.db_name)
        rv = []
        _now = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if _now < v[0] and v[2] == 'orange':
                rv.append(k)
        db.close()
        return rv

    def mac_list_get_all_orange_macs(self) -> list:
        """ return keys (macs) w/ timestamp NOT expired """

        db = shelve.open(self.db_name)
        rv = []
        _now = datetime.datetime.now().timestamp()
        for k, v in db.items():
            if v[2] == 'orange':
                rv.append(k)
        db.close()
        return rv

    def mac_list_get_all_black_macs(self) -> list:
        """ return keys (macs) w/ timestamp NOT expired """

        db = shelve.open(self.db_name)
        rv = []
        for k, v in db.items():
            if v[2] == 'black':
                rv.append(k)
        db.close()
        return rv

    def mac_list_filter_orange_macs(self, in_macs):
        """ return 'in_macs' entries NOT PRESENT in mac_orange_list"""

        o = self.mac_list_get_all_orange_macs_not_expired()
        return [i for i in in_macs if i not in o]

    def mac_list_prune_black(self):
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

    def mac_list_filter_black_macs(self, in_macs):
        """ prune() black mac list, return 'in_macs' entries NOT PRESENT in it """

        self.mac_list_prune_black()
        b = self.mac_list_get_all_black_macs()
        return [i for i in in_macs if i not in b]


def filter_white_macs(wl, in_macs) -> list:
    return [i for i in in_macs if i in wl]


# for secret EDIT tab purge() buttons
def black_macs_delete_all(name):
    ml = ColorMacList(name, None)
    ml.mac_list_delete_file()


def bluepy_scan_results_to_strings(sr):
    return [i.addr for i in sr]
