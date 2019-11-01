from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject


class SignalsBLE(QObject):
    ble_scan_start = pyqtSignal()
    ble_scan_result = pyqtSignal(object)
    ble_dl_session = pyqtSignal(str, int, int)
    ble_dl_logger = pyqtSignal()
    ble_dl_file = pyqtSignal(str, int, int, int)
    ble_dl_file_ = pyqtSignal(int, int)
    ble_dl_logger_ = pyqtSignal(str, int)
    ble_dl_session_ = pyqtSignal(str)
    error = pyqtSignal(str)
    error_gui = pyqtSignal(str)
    status = pyqtSignal(str)
    status_gui = pyqtSignal(str)


class SignalsGPS(QObject):
    status_gui = pyqtSignal(str)
    status = pyqtSignal(str)
    error_gui = pyqtSignal(str)
    error = pyqtSignal(str)
    gps_result = pyqtSignal(str, str, str, str)
    gps_update = pyqtSignal(bool, str, str)
    internet_result = pyqtSignal(bool, str)



class SignalsPLT(QObject):
    status = pyqtSignal(str)
    debug = pyqtSignal(str)
    status_gui = pyqtSignal(str)
    plt_result = pyqtSignal(object)
    error_gui = pyqtSignal(str)
    error = pyqtSignal(str)
    clk_start = pyqtSignal()
    clk_end = pyqtSignal()
    status_gui_clear = pyqtSignal()


class SignalsGUI(QObject):
    gui_tick = pyqtSignal(str)
