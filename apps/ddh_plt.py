import numpy as np
from .ddh_db import LIAvgDB
from .ddh_utils import (
    mac_from_folder,
    lid_files_to_csv,
    csv_to_data_frames,
    del_frames_before,
    slice_n_average,
    plot_format_time_labels,
    plot_format_time_ticks,
    plot_format_title,
    json_mac_dns,
    metric_to_column_name,
    plot_line_color,
)


class DeckDataHubPLT:

    # state
    current_plots = []
    last_metric = None
    last_folder = None
    last_ts = None
    last_ax = None

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
        # metadata and signals
        f = folder.split('/')[-1]
        c0 = metric_to_column_name(metric[0])
        c1 = metric_to_column_name(metric[1])
        lbl = json_mac_dns(mac_from_folder(folder))
        clr0 = plot_line_color(c0)
        clr1 = plot_line_color(c1)
        signals.clk_start.emit()
        signals.status.emit('PLT: {} for {}'.format(ts, folder))

        # query database for the data, or process it from scratch
        try:
            t, y0 = DeckDataHubPLT.plt_cache_query(signals, folder, ts, metric[0])
            _, y1 = DeckDataHubPLT.plt_cache_query(signals, folder, ts, metric[1])
        except (AttributeError, Exception):
            # e = 'No {}({}) for\n{}'.format(metric, ts, f)
            # signals.error_gui.emit(e)
            # e = 'PLT: no {}({}) for {}'.format(metric, ts, f)
            e = 'PLT: E1'
            signals.error.emit(e)
            signals.plt_result.emit(False)
            signals.clk_end.emit()
            return

        # need at least two points to plot a line
        if np.count_nonzero(~np.isnan(y0)) < 2:
            # e = 'Few plot {}({}) points for {}'.format(metric, ts, f)
            # signals.error_gui.emit(e)
            # e = 'PLT: few {}({}) points for {}'.format(metric, ts, f)
            e = 'PLT: E2'
            signals.error.emit(e)
            signals.plt_result.emit(False)
            signals.clk_end.emit()
            return

        # brand new base plot or additional metric line to base plot
        cnv.figure.clf()
        cnv.figure.tight_layout()
        ax = cnv.figure.add_subplot(111)
        ax.set_ylabel(c0, fontsize='large', fontweight='bold', color=clr0)
        ax.tick_params(axis='y', labelcolor=clr0)
        ax.plot(t, y0, label=lbl, color=clr0)
        ax.set_xlabel('time', fontsize='large', fontweight='bold')
        ax.set_title('Logger ' + lbl + ', ' + plot_format_title(t, ts), fontsize='x-large')

        # build second, additional metric to existing base
        ax2 = ax.twinx()
        ax2.set_ylabel(c1, fontsize='large', fontweight='bold', color=clr1)
        ax2.tick_params(axis='y', labelcolor=clr1)
        ax2.plot(t, y1, '--', label=lbl, color=clr1)

        # format it properly
        lbs = plot_format_time_ticks(t, ts)
        ax.set_xticks(lbs)
        ax2.set_xticks(lbs)
        ax.set_xticklabels(plot_format_time_labels(lbs, ts))
        cnv.draw()

        # signal we finished plotting
        signals.plt_result.emit(True)
        signals.clk_end.emit()
