from matplotlib import rcParams
from .ddh_utils import (
    extract_mac_from_folder,
    all_lid_to_csv,
    csv_to_data_frames,
    rm_frames_pre,
    slice_n_average,
)


class DeckDataHubPLT:

    @staticmethod
    def plt_plot(signals, folders, cnv, ts, metric):
        signals.clk_start.emit()

        # obtain 'metric' data from 'folders'
        all_lid_to_csv(folders)
        df1, df2 = csv_to_data_frames(folders, metric)

        # only keep data within span of last recorded time
        t, y = rm_frames_pre(df1, ts, metric)

        # slice and average data
        t, y_avg = slice_n_average(t, y, ts)

        # obtain data for plot meta-information, legend
        mac_1 = extract_mac_from_folder(folders[0])

        # plot, rcParams update needed to show x-axis label
        rcParams.update({'figure.autolayout': True})
        axes = cnv.figure.subplots()
        axes.plot(t, y_avg)
        axes.axis('tight')
        cnv.draw()

        # signal we are done with plotting
        signals.plt_result.emit(True)
        signals.clk_end.emit()
