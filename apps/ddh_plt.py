import json
import sqlite3
import numpy as np
from matplotlib.ticker import FormatStrFormatter

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
            time_span       TEXT, \
            metric          TEXT, \
            the_times       TEXT, \
            the_values      TEXT  \
            )"
        )
        db.commit()
        c.close()

    # v is a list which gets converted to string
    def add_record(self, w, s, e, p, m, t, v):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('INSERT INTO records('
                  'mac, start_time, end_time, time_span,'
                  'metric, the_times, the_values) '
                  'VALUES(?,?,?,?,?,?,?)',
                  (w, s, e, p, m, json.dumps(t), json.dumps(v)))
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
        return json.loads(self.get_record(record_id)[7])

    def get_record_times(self, record_id):
        return json.loads(self.get_record(record_id)[6])

    def get_record_id(self, w, s, e, p, m):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT id from records WHERE mac=? AND '
                  'start_time=? AND end_time=? AND time_span=?'
                  'AND metric=?', (w, s, e, p, m))
        records = c.fetchall()
        c.close()
        return records[0]

    def does_record_exist(self, w, s, e, p, m):
        db = sqlite3.connect(self.dbfilename)
        c = db.cursor()
        c.execute('SELECT EXISTS(SELECT 1 from records WHERE mac=? AND '
                  'start_time=? AND end_time=? AND time_span=?'
                  'AND metric=?)', (w, s, e, p, m))
        records = c.fetchall()
        c.close()
        return records[0][0]


class DeckDataHubPLT:

    # state
    current_plots = []
    last_metric = None
    last_folder = None
    last_ts = None
    last_ax = None

    @staticmethod
    def plt_error(signals, e):
        signals.error.emit(e)
        signals.plt_result.emit(False)
        signals.clk_end.emit()

    @staticmethod
    def plt_cache_query(signals, folder, ts, metric):
        # collect metadata
        c = metric_to_column_name(metric)
        mac = mac_from_folder(folder)

        # load and prune data within most recent 'ts'
        lid_files_to_csv(folder)
        df = csv_to_data_frames(folder, metric)
        x, y = del_frames_before(df, ts, c)
        s, e = x.values[0], x.values[-1]

        # database check...
        db = LIAvgDB()
        if db.does_record_exist(mac, s, e, ts, c):
            # ... success! we already had this data in cache
            signals.status.emit('PLT: cache hit')
            r_id = db.get_record_id(mac, s, e, ts, c)
            t = db.get_record_times(r_id)
            y_avg = db.get_record_values(r_id)
            return t, y_avg

        # nope, let's process and cache this data for the future
        t, y_avg = slice_n_average(x, y, ts)
        db.add_record(mac, s, e, ts, c, t, y_avg)
        return t, y_avg

    @staticmethod
    def plt_plot(signals, folder, cnv, ts, metric):
        # signals and metadata
        signals.clk_start.emit()
        signals.status.emit('PLT: {}({}) for {}'.format(metric, ts, folder))
        c = metric_to_column_name(metric)
        lbl = mac_dns(mac_from_folder(folder))
        clr = line_color(c)

        # query database for this data, or process it from scratch
        try:
            t, y = DeckDataHubPLT.plt_cache_query(signals, folder, ts, metric)
        except (AttributeError, Exception):
            e = 'PLT: can\'t {}({}) for {}'.format(metric, ts, folder)
            return DeckDataHubPLT.plt_error(signals, e)

        # don't plot something already there
        p = [folder, ts, metric]
        if p in DeckDataHubPLT.current_plots:
            signals.plt_result.emit(True)
            signals.clk_end.emit()
            return

        # need at least two points to plot a line
        if np.count_nonzero(~np.isnan(y)) < 2:
            e = 'PLT: few {}({}) points for {}'.format(metric, ts, folder)
            return DeckDataHubPLT.plt_error(signals, e)

        # find out metric number we are plotting
        same_folder = (DeckDataHubPLT.last_folder == folder)
        same_ts = (DeckDataHubPLT.last_ts == ts)
        same_metric = (DeckDataHubPLT.last_metric == metric)
        if same_folder and same_ts and not same_metric:
            # second metric, additional to an existing plot
            ax = DeckDataHubPLT.last_ax
            bx = ax.twinx()
            bx.set_ylabel(c, fontsize='large', fontweight='bold', color=clr)
            bx.tick_params(axis='y', labelcolor=clr)
            bx.plot(t, y, label=lbl, color=clr)
        else:
            # first one, brand new axis (not axes)
            DeckDataHubPLT.current_plots = []
            cnv.figure.clf()
            cnv.figure.tight_layout()
            ax = cnv.figure.add_subplot(111)
            ax.set_ylabel(c, fontsize='large', fontweight='bold', color=clr)
            ax.tick_params(axis='y', labelcolor=clr)
            ax.plot(t, y, label=lbl, color=clr)

        # plot labels, axes and legends
        DeckDataHubPLT.current_plots.append(p)
        lbs = format_time_ticks(t, ts)
        ax.set_xticks(lbs)
        ax.set_xticklabels(format_time_labels(lbs, ts))
        ax.set_xlabel('time', fontsize='large', fontweight='bold')
        ax.set_title('Logger ' + lbl + ', ' + format_title(t, ts), fontsize='x-large')
        # ax.legend()
        cnv.draw()

        # save context
        DeckDataHubPLT.last_folder = folder
        DeckDataHubPLT.last_ts = ts
        DeckDataHubPLT.last_metric = metric
        DeckDataHubPLT.last_ax = ax

        # signal we finished plotting
        signals.plt_result.emit(True)
        signals.clk_end.emit()
