import pytest
import sys
from ddh.threads.utils_macs import BlackMacList, black_macs_delete_all


db_name = 'test.db'


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
class TestBlackMacs:
    def test_black_destroy_and_one(self):
        bm = BlackMacList(db_name, None)
        black_macs_delete_all(db_name)
        _mac = '11:11:11:11:11:11'
        _till = 100
        bm.ls.macs_add_or_update(_mac, _till)
        n = bm.ls.len_macs_list()
        assert n == 1

    def test_black_macs_prune(self):
        bm = BlackMacList(db_name, None)
        black_macs_delete_all(db_name)
        _mac = '11:11:11:11:11:11'
        _till = -100
        bm.ls.macs_add_or_update(_mac, _till)
        _mac = '22:22:22:22:22:22'
        _till = 100
        bm.ls.macs_add_or_update(_mac, _till)
        bm._macs_prune()
        n = bm.ls.len_macs_list()
        assert n == 1

    def test_black_macs_how_many_pending(self):
        bm = BlackMacList(db_name, None)
        black_macs_delete_all(db_name)
        _mac = '11:11:11:11:11:11'
        _till = -100
        bm.ls.macs_add_or_update(_mac, _till)
        _mac = '22:22:22:22:22:22'
        _till = 100
        bm.ls.macs_add_or_update(_mac, _till)
        # prune will be done inside
        _scan_result = ['22:22:22:22:22:22']
        n = len(bm.filter_black_macs(_scan_result))
        assert n == 0
        _scan_result = ['33:33:33:33:33:33']
        n = len(bm.filter_black_macs(_scan_result))
        assert n == 1
