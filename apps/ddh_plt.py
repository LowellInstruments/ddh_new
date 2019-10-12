import matplotlib.pyplot as plt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QSizePolicy
from matplotlib import rcParams
from .ddh_utils import (
    extract_mac_from_folder,
    convert_lid_files_to_csv,
    convert_csv_to_data_frames,
)


class DeckDataHubPLT:

    @staticmethod
    def plt_plot(signals, folders, cnv, ts, metric):
        signals.clk_start.emit()

        # obtain 'metric' data from 'folders' and trim it by 'ts' time
        convert_lid_files_to_csv(folders)
        df1, df2 = convert_csv_to_data_frames(folders, metric)
        df1, df2 = discard_frames_before(ts, df1, df2)

        # plot stuff
        a1 = extract_mac_from_folder(folders[0])
        a2 = extract_mac_from_folder(folders[1])

        x_time = df1['ISO 8601 Time'].compute()
        y_data = df1[metric].compute()
        plt.plot(x_time, y_data)
        plt.axis('tight')
        print('hi')
        plt.show()
        print('bye')
        signals.plt_result.emit(True)
        signals.clk_end.emit()
