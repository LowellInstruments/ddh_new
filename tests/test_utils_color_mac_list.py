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
        ml.mac_list_delete_file()
        inc = 100
        ml.mac_list_add_or_update(MAC_B, inc, 0, 'black')
        ml.mac_list_add_or_update(MAC_O, inc, 2, 'orange')
        return ml

    def test_mac_list_delete_file(self):
        ml = self._prep()
        assert ml.mac_list_delete_file() == 0
        assert ml.mac_list_delete_file() == 1

    def test_mac_list_del_one(self):
        ml = self._prep()
        assert ml.mac_list_len() == 2
        ml.mac_list_del_one(MAC_B)
        assert ml.mac_list_len() == 1
        assert MAC_B not in ml.mac_list_get_all_macs()
        assert MAC_O in ml.mac_list_get_all_macs()
        assert ml.mac_list_len() == 1

    def test_mac_list_get_del_one(self):
        ml = self._prep()
        rv = ml.mac_list_get_one(MAC_B)
        assert rv
        ml.mac_list_del_one(MAC_B)
        rv = ml.mac_list_get_one(MAC_B)
        assert not rv

    def test_mac_list_update_one(self):
        ml = self._prep()
        rv = ml.mac_list_get_one(MAC_B)
        t1 = rv[0]
        # t1: perf_counter() + 100
        inc = 200
        ml.mac_list_add_or_update(MAC_B, inc, 0, 'black')
        rv = ml.mac_list_get_one(MAC_B)
        t2 = rv[0]
        assert t2 > time.perf_counter() + 175






