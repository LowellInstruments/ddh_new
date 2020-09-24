import pytest
import sys
from db.db_his import DBHis


db_n = 'test.db'


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
class TestDDHDBHis:
    def test_constructor(self):
        assert DBHis(db_n)

    def test_add_record(self):
        db = DBHis(db_n)
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.add_record('11:11:11:11:11:11', 'name_1', 'lat_1', 'lon_1', t)
        i = db.get_record_id('11:11:11:11:11:11')
        c = db.count_records()
        assert (i == 1)
        assert (c == 1)

    def test_update_record_existing(self):
        db = DBHis(db_n)
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.add_record('11:11:11:11:11:11', 'name_1', 'lat_1', 'lon_1', t)
        db.update_record('11:11:11:11:11:11', 'hello', 'lat_1', 'lon_1', t, 1)
        r = db.get_record(1)
        c = db.count_records()
        assert (r[2] == 'hello')
        assert (c == 1)

    def test_delete_all_records(self):
        db = DBHis(db_n)
        db.delete_all_records()
        c = db.count_records()
        assert (c == 0)

    def test_count_records(self):
        db = DBHis(db_n)
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.add_record('11:11:11:11:11:11', 'name_1', 'lat_1', 'lon_1', t)
        db.add_record('22:22:22:22:22:22', 'name_2', 'lat_2', 'lon_2', t)
        c = db.count_records()
        assert (c == 2)

    def test_record_exist(self):
        db = DBHis(db_n)
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.add_record('11:11:11:11:11:11', 'name_1', 'lat_1', 'lon_1', t)
        e = db.does_record_exist('11:11:11:11:11:11')
        assert (e == 1)
        e = db.does_record_exist('66:66:66:66:66:66')
        assert (e == 0)

    def test_get_recent_records(self):
        db = DBHis(db_n)
        r = db.get_recent_records()
        pass

    def test_safe_update_existing(self):
        db = DBHis(db_n)
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.add_record('11:11:11:11:11:11', 'name_1', 'lat_1', 'lon_1', t)
        db.safe_update('11:11:11:11:11:11', 'name_2', 'lat_2', 'lon_2', t)
        r = db.get_record(1)
        c = db.count_records()
        assert (r[2] == 'name_2')
        assert (c == 1)

    def test_safe_update_non_existing(self):
        db = DBHis(db_n)
        db.delete_all_records()
        t = '2019-11-25T09:41:34.000'
        db.safe_update('11:11:11:11:11:11', 'name_2', 'lat_2', 'lon_2', t)
        r = db.get_record(1)
        c = db.count_records()
        assert (r[2] == 'name_2')
        assert (c == 1)

