from db.db_his import DBHis

if __name__ == '__main__':
    db = DBHis('./db_his_mp.db')
    rr = db.list_all_records()

    for _ in rr:
        print(_)

        # c.execute(
        #     "CREATE TABLE IF NOT EXISTS records\
        #     ( \
        #     id              INTEGER PRIMARY KEY, \
        #     mac             TEXT, \
        #     name            TEXT, \
        #     lat             TEXT, \
        #     lon             TEXT, \
        #     sws_time        TEXT  \
        #     )"
        # )

