from .ddh_utils import (
    extract_mac_from_folder,
    all_lid_to_csv,
    csv_to_data_frames,
    rm_frames_before,
    slice_n_average,
    format_time_labels,
    format_time_ticks,
    format_title,
    get_logger_name
)


class DeckDataHubPLT:

    @staticmethod
    def plt_plot(signals, folders, cnv, ts, metric):
        signals.clk_start.emit()

        # obtain metadata
        mac_1 = extract_mac_from_folder(folders[0])
        mac_2 = extract_mac_from_folder(folders[1])

        # obtain 'metric' data from 'folders'
        all_lid_to_csv(folders)
        df1, df2 = csv_to_data_frames(folders, metric)

        # only keep data within span of last recorded time
        t, y = rm_frames_before(df1, ts, metric)
        _, k = rm_frames_before(df2, ts, metric)

        # slice and average data
        t2 = t
        t, y_avg = slice_n_average(t, y, ts)
        _, k_avg = slice_n_average(t2, k, ts)

        # plot reset and axes
        cnv.figure.clf()
        ax = cnv.figure.add_subplot(111)
        ax.plot(t, y_avg, label=get_logger_name(mac_1))
        ax.plot(t, k_avg, label=get_logger_name(mac_2)) if mac_2 else True

        # plot labels and legends
        lbs = format_time_ticks(t, ts)
        ax.set_xticks(lbs)
        ax.set_xticklabels(format_time_labels(lbs, ts))
        ax.set_ylabel('Temperature (C)', fontsize='large', fontweight='bold')
        ax.set_xlabel('time', fontsize='large', fontweight='bold')
        ax.set_title(format_title(t, ts), fontsize='large')
        ax.legend()
        cnv.draw()

        # signal we are done with plotting
        signals.plt_result.emit(True)
        signals.clk_end.emit()
