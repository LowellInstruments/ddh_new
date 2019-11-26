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
        c = metric_to_column_name(metric)
        lbl = json_mac_dns(mac_from_folder(folder))
        clr = plot_line_color(c)
        signals.clk_start.emit()
        signals.status.emit('PLT: {}({}) for {}'.format(metric, ts, folder))

        # query database for the data, or process it from scratch
        try:
            t, y = DeckDataHubPLT.plt_cache_query(signals, folder, ts, metric)
        except (AttributeError, Exception):
            e = 'No {}({}) for\n{}'.format(metric, ts, f)
            signals.error_gui.emit(e)
            e = 'PLT: no {}({}) for {}'.format(metric, ts, f)
            signals.error.emit(e)
            signals.plt_result.emit(False)
            signals.clk_end.emit()
            return

        # don't plot something already being displayed
        p = [folder, ts, metric]
        if p in DeckDataHubPLT.current_plots:
            signals.plt_result.emit(True)
            signals.clk_end.emit()
            return

        # need at least two points to plot a line
        if np.count_nonzero(~np.isnan(y)) < 2:
            e = 'Few plot {}({}) points for {}'.format(metric, ts, f)
            signals.error_gui.emit(e)
            e = 'PLT: few {}({}) points for {}'.format(metric, ts, f)
            signals.error.emit(e)
            signals.plt_result.emit(False)
            signals.clk_end.emit()
            return

        # brand new base plot or additional metric line to base plot
        same_folder = (DeckDataHubPLT.last_folder == folder)
        same_ts = (DeckDataHubPLT.last_ts == ts)
        same_metric = (DeckDataHubPLT.last_metric == metric)
        print('same_folder {}'.format(same_folder))
        print('same_ts {}'.format(same_ts))
        print('same_metric {}'.format(same_metric))
        if same_folder and same_ts and not same_metric:
            # build second, additional metric to existing base
            ax = DeckDataHubPLT.last_ax.twinx()
            ax.set_ylabel(c, fontsize='large', fontweight='bold', color=clr)
            ax.tick_params(axis='y', labelcolor=clr)
            ax.plot(t, y, label=lbl, color=clr)
        else:
            # build first, base plot
            DeckDataHubPLT.current_plots = []
            cnv.figure.clf()
            cnv.figure.tight_layout()
            ax = cnv.figure.add_subplot(111)
            ax.set_ylabel(c, fontsize='large', fontweight='bold', color=clr)
            ax.tick_params(axis='y', labelcolor=clr)
            ax.plot(t, y, label=lbl, color=clr)
            ax.set_xlabel('time', fontsize='large', fontweight='bold')
            ax.set_title('Logger ' + lbl + ', ' + plot_format_title(t, ts), fontsize='x-large')
            # ax.legend()

            # save base plot's context
            DeckDataHubPLT.last_folder = folder
            DeckDataHubPLT.last_ts = ts
            DeckDataHubPLT.last_metric = metric
            DeckDataHubPLT.last_ax = ax

        # add built plot, either base or additional, and draw it
        lbs = plot_format_time_ticks(t, ts)
        ax.set_xticks(lbs)
        ax.set_xticklabels(plot_format_time_labels(lbs, ts))
        DeckDataHubPLT.current_plots.append(p)
        cnv.draw()

        # signal we finished plotting
        signals.plt_result.emit(True)
        signals.clk_end.emit()
