import time
import pytest
import sys
from ddh.threads.utils_macs import ColorMacList


db_name = 'color_mac_list.db'
MAC_B = '11:11:11:11:11:11'
MAC_O = '22:22:22:22:22:22'


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
class TestColorMacList:
    @staticmethod
    def _prep():
        ml = ColorMacList(db_name, None)
        ml.delete_color_mac_file()
        inc = 100
        ml.entry_add_or_update(MAC_B, inc, 0, 'black')
        ml.entry_add_or_update(MAC_O, inc, 4, 'orange')
        return ml

    def test_mac_list_delete_file(self):
        ml = self._prep()
        assert ml.delete_color_mac_file() == 0
        assert ml.delete_color_mac_file() == 1

    def test_mac_list_del_one(self):
        ml = self._prep()
        assert ml.mac_list_len() == 2
        ml.entry_delete(MAC_B)
        assert ml.mac_list_len() == 1
        assert MAC_B not in ml.macs_get_all()
        assert MAC_O in ml.macs_get_all()
        assert ml.mac_list_len() == 1

    def test_mac_list_get_del_one(self):
        ml = self._prep()
        rv = ml.entry_get(MAC_B)
        assert rv
        ml.entry_delete(MAC_B)
        rv = ml.entry_get(MAC_B)
        assert not rv

    def test_mac_list_update_one(self):
        ml = self._prep()
        rv = ml.entry_get(MAC_B)
        t1 = rv[0]
        # t1: perf_counter() + 100
        inc = 200
        ml.entry_add_or_update(MAC_B, inc, 0, 'black')
        rv = ml.entry_get(MAC_B)
        t2 = rv[0]
        assert t2 > time.perf_counter() + 175

    def test_mac_entries_get_all_orange(self):
        ml = self._prep()
        rv = ml.entries_get_all_orange()
        assert len(rv) == 1
        assert MAC_O in rv.keys()

    def test_retries_get_from_orange_mac(self):
        ml = self._prep()
        rv = ml.retries_get_from_orange_mac(MAC_O)
        assert rv == 4






