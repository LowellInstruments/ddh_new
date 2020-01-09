import pytest
import sys
from apps.ddh_db_his import DBHis


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
class TestDDHDBHis:
    def test_constructor(self):
        assert DBHis()

    def test_add_record(self):
        db = DBHis()
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.add_record('11:11:11:11:11:11', 'name_1', t)
        i = db.get_record_id('11:11:11:11:11:11')
        c = db.count_records()
        assert (i == 1)
        assert (c == 1)

    def test_update_record(self):
        db = DBHis()
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.add_record('11:11:11:11:11:11', 'name_1', t)
        db.update_record('11:11:11:11:11:11', 'hello', t, 1)
        r = db.get_record(1)
        c = db.count_records()
        assert (r[2] == 'hello')
        assert (c == 1)

    def test_delete_all_records(self):
        db = DBHis()
        db.delete_all_records()
        c = db.count_records()
        assert (c == 0)

    def test_count_records(self):
        db = DBHis()
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.add_record('11:11:11:11:11:11', 'name_1', t)
        db.add_record('22:22:22:22:22:22', 'name_2', t)
        c = db.count_records()
        assert (c == 2)

    def test_record_exist(self):
        db = DBHis()
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.add_record('11:11:11:11:11:11', 'name_1', t)
        e = db.does_record_exist('11:11:11:11:11:11')
        assert (e == 1)
        e = db.does_record_exist('66:66:66:66:66:66')
        assert (e == 0)
