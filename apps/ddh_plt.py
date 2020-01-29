import numpy as np
from .ddh_db_plt import DBPlt
from .ddh_utils import (
    mac_from_folder,
    lid_to_csv,
    csv_to_df,
    rm_df_before,
    slice_n_avg,
    plot_format_time_labels,
    plot_format_time_ticks,
    plot_format_title,
    json_mac_dns,
    plot_metric_to_column_name,
    plot_line_color,
    plot_metric_to_label_name
)


class DeckDataHubPLT:

    # state
    current_plots = []
    last_metric = None
    last_folder = None
    last_ts = None
    last_ax = None

    @staticmethod
    def _db_cache_maybe(signals, folder, ts, metric):
        # metadata
        c = plot_metric_to_column_name(metric)
        mac = mac_from_folder(folder)

        # load + prune data within last 'ts'
        lid_to_csv(folder)
        df = csv_to_df(folder, metric)
        x, y = rm_df_before(df, ts, c)
        s, e = x.values[0], x.values[-1]

        # DBPlt cache check
        db = DBPlt()
        if db.does_record_exist(mac, s, e, ts, c):
            # yey! already have this data in cache
            signals.status.emit('PLT: cache hit')
            r_id = db.get_record_id(mac, s, e, ts, c)
            t = db.get_record_times(r_id)
            y_avg = db.get_record_values(r_id)
            return t, y_avg

        # not cached, process data and cache
        t, y_avg = slice_n_avg(x, y, ts)
        db.add_record(mac, s, e, ts, c, t, y_avg)
        return t, y_avg

    @staticmethod
    def plt_plot(signals, folder, cnv, ts, pairs_of_metrics):
        f = folder.split('/')[-1]
        lg = json_mac_dns(mac_from_folder(folder))
        signals.clk_start.emit()
        signals.plt_start.emit()

        # try to plot any metric of a logger
        for pair in pairs_of_metrics:
            if ddh_p._plot(signals, folder, cnv, ts, pair):
                signals.plt_result.emit(True)
                signals.clk_end.emit()
                return
            else:
                a = (pair, ts, lg, f)
                e = 'PLT: no {}({}) plots for \'{}\'({})'.format(*a)
                signals.error.emit(e)
                signals.plt_msg.emit(e)

        # we could not plot any pair of metrics
        signals.plt_result.emit(False)
        signals.clk_end.emit()

    @staticmethod
    def _plot(signals, folder, cnv, ts, metric_pair):
        # metadata and signals
        m_p = metric_pair
        f = folder.split('/')[-1]
        c0 = plot_metric_to_column_name(m_p[0])
        c1 = plot_metric_to_column_name(m_p[1])
        a0 = plot_metric_to_label_name(m_p[0])
        a1 = plot_metric_to_label_name(m_p[1])
        lg = json_mac_dns(mac_from_folder(folder))
        clr0 = plot_line_color(c0)
        clr1 = plot_line_color(c1)
        signals.status.emit('PLT: {}({}) for {}'.format(m_p, ts, f))

        # query database for 1st metric in pair, important one
        try:
            t, y0 = DeckDataHubPLT._db_cache_maybe(signals, folder, ts, m_p[0])
        except (AttributeError, Exception):
            e = 'PLT: no {}({}) for {}'.format(m_p[0], ts, f)
            signals.error.emit(e)
            signals.plt_msg.emit(e)
            return False

        # query DB for 2nd metric in pair, not critical
        try:
            _, y1 = DeckDataHubPLT._db_cache_maybe(signals, folder, ts, m_p[1])
        except (AttributeError, Exception):
            e = 'PLT: no {}({}) for {}'.format(m_p[1], ts, f)
            y1 = None
            signals.error.emit(e)
            signals.plt_msg.emit(e)

        # need at least two points to plot a 1st data line
        if np.count_nonzero(~np.isnan(y0)) < 2:
            e = 'PLT: few {}({}) data for {}'.format(m_p, ts, f)
            signals.error.emit(e)
            signals.plt_msg.emit(e)
            return False

        # prepare for plotting 1st data y0
        cnv.figure.clf()
        cnv.figure.tight_layout()
        tit = plot_format_title(t, ts)
        ax1 = cnv.figure.add_subplot(111)
        sym = '{} '.format('\u2014')
        ax1.set_ylabel(sym + a0, fontsize='large', fontweight='bold', color=clr0)
        ax1.tick_params(axis='y', labelcolor=clr0)

        # hack for pressure / depth display
        if a0 == 'Depth (m)':
            ax1.invert_yaxis()

        ax1.plot(t, y0, label=a0, color=clr0)
        ax1.set_xlabel('time', fontsize='large', fontweight='bold')
        ax1.set_title('Logger ' + lg + ', ' + tit, fontsize='x-large')
        lbs = plot_format_time_ticks(t, ts)

        # prepare for plotting 2nd data, y1, if any
        if y1:
            sym = '- -  '
            ax2 = ax1.twinx()
            ax2.set_ylabel(sym + a1, fontsize='large', fontweight='bold', color=clr1)
            ax2.tick_params(axis='y', labelcolor=clr1)

            # hack for pressure / depth display
            if a1 == 'Depth (m)':
                ax2.invert_yaxis()

            ax2.plot(t, y1, '--', label=a1, color=clr1)
            ax2.set_xticks(lbs)

        # common labels MUST be formatted here, at the end
        # cnv.figure.legend(bbox_to_anchor=[0.9, 0.5], loc='center right')
        ax1.set_xticklabels(plot_format_time_labels(lbs, ts))
        ax1.set_xticks(lbs)
        cnv.draw()
        return True


ddh_p = DeckDataHubPLT
