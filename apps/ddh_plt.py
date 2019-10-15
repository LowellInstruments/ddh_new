from .ddh_utils import (
    extract_mac_from_folder,
    all_lid_to_csv,
    csv_to_data_frames,
    rm_frames_before,
    slice_n_average,
    format_time_labels,
    format_time_ticks,
    format_title,
    mac_dns,
    metric_to_column_name,
    line_color,
    line_style
)
import numpy as np


class DeckDataHubPLT:

    @staticmethod
    def plt_plot(signals, folders, cnv, ts, metric):
        # signals and metadata
        signals.clk_start.emit()
        mac_1 = extract_mac_from_folder(folders[0])
        mac_2 = extract_mac_from_folder(folders[1])
        signals.status.emit('PLT: {} {} vs {}'.format(metric, mac_1, mac_2))

        # obtain 'metric' data from 'folders'
        all_lid_to_csv(folders)
        df1, df2 = csv_to_data_frames(folders, metric)

        # only keep data within span of last recorded time
        c = metric_to_column_name(metric)
        t, y = rm_frames_before(df1, ts, c)
        _, k = rm_frames_before(df2, ts, c)

        # slice and get averaged data as lists
        t2 = t
        t, y_avg = slice_n_average(t, y, ts)
        _, k_avg = slice_n_average(t2, k, ts)

        # e.g. asked metric not existent for folder_1
        if not t:
            signals.plt_result.emit(False)
            signals.clk_end.emit()
            return

        # build first folder's axes
        cnv.figure.clf()
        ax = cnv.figure.add_subplot(111)
        ax.plot(t, y_avg, label=mac_dns(mac_1), color=line_color(c, 1))

        # maybe build second folder's axes
        if not np.isnan(k_avg).all():
            ax.plot(t, k_avg, label=mac_dns(mac_2),
                    color=line_color(c, 2), linestyle=line_style(c))

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
