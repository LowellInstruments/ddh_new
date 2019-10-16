import json
import sqlite3

from .ddh_utils import (
    mac_from_folder,
    lid_files_to_csv,
    csv_to_data_frames,
    del_frames_before,
    slice_n_average,
    format_time_labels,
    format_time_ticks,
    format_title,
    mac_dns,
    metric_to_column_name,
    line_color,
)


class LIAvgDB:
    def __init__(self):
        self.dbfilename = 'ddh_avg.db'
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute(
            "CREATE TABLE IF NOT EXISTS records\
            ( \
            id              INTEGER PRIMARY KEY, \
            mac             TEXT, \
            start_time      TEXT, \
            end_time        TEXT, \
            metric          TEXT, \
            the_times       TEXT, \
            the_values      TEXT  \
            )"
        )
        db.commit()
        c.close()

    # v is a list which gets converted to string
    def add_record(self, w, s, e, m, t, v):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('INSERT INTO records('
                  'mac, start_time, end_time, metric, the_times, the_values) \
                  VALUES(?,?,?,?,?,?)',
                  (w, s, e, m, json.dumps(t), json.dumps(v)))
        db.commit()
        c.close()

    def delete_record(self, record_id):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('DELETE FROM records where id=?', (record_id,))
        db.commit()
        c.close()

    def list_all_records(self, ):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT * from records')
        records = c.fetchall()
        c.close()
        return records

    def get_record(self, record_id):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT * from records WHERE id=?', record_id)
        records = c.fetchall()
        c.close()
        return records[0]

    def get_record_values(self, record_id):
        return json.loads(self.get_record(record_id)[6])

    def get_record_times(self, record_id):
        return json.loads(self.get_record(record_id)[5])

    def get_record_id(self, w, s, e, m):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT id from records WHERE mac=? AND '
                  'start_time=? AND end_time=? AND metric=?', (w, s, e, m))
        records = c.fetchall()
        c.close()
        return records[0]

    def does_record_exist(self, w, s, e, m):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT EXISTS(SELECT 1 from records WHERE mac=? AND '
                  'start_time=? AND end_time=? AND metric=?)', (w, s, e, m))
        records = c.fetchall()
        c.close()
        return records[0][0]


class DeckDataHubPLT:

    @staticmethod
    def plt_cache_query(signals, folder, ts, metric):
        # collect metadata
        c = metric_to_column_name(metric)
        mac = mac_from_folder(folder)

        # shape data to work with
        lid_files_to_csv(folder)
        df = csv_to_data_frames(folder, metric)
        x, y = del_frames_before(df, ts, c)
        s, e = x.values[0], x.values[-1]

        # check if we already calculated this previously
        db = LIAvgDB()
        if db.does_record_exist(mac, s, e, c):
            signals.status.emit('PLT: cache hit')
            r_id = db.get_record_id(mac, s, e, c)
            t = db.get_record_times(r_id)
            y_avg = db.get_record_values(r_id)
        else:
            t, y_avg = slice_n_average(x, y, ts)
            db.add_record(mac, s, e, c, t, y_avg)

        return t, y_avg

    @staticmethod
    def plt_plot(signals, folder, cnv, ts, metric):
        # signals and metadata
        signals.clk_start.emit()
        signals.status.emit('PLT: {} for {}'.format(metric, folder))

        # maybe database has this query
        try:
            t, y = DeckDataHubPLT.plt_cache_query(signals, folder, ts, metric)
        except (AttributeError, Exception):
            signals.error.emit('PLT: can\'t {} for {}'.format(metric, folder))
            signals.plt_result.emit(False)
            signals.clk_end.emit()
            return

        # build first folder's axes
        cnv.figure.clf()
        c = metric_to_column_name(metric)
        lbl = mac_dns(mac_from_folder(folder))
        clr = line_color(c)
        ax = cnv.figure.add_subplot(111)
        ax.plot(t, y, label=lbl, color=clr)

        # plot labels and legends
        lbs = format_time_ticks(t, ts)
        ax.set_xticks(lbs)
        ax.set_xticklabels(format_time_labels(lbs, ts))
        ax.set_xlabel('time', fontsize='large', fontweight='bold')
        ax.set_ylabel(c, fontsize='large', fontweight='bold')
        ax.set_title(format_title(t, ts), fontsize='large')
        ax.legend()
        cnv.draw()

        # signal we are done with plotting
        signals.plt_result.emit(True)
        signals.clk_end.emit()
