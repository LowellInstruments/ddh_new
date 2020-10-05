from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject


class SignalsBLE(QObject):
    ble_scan_pre = pyqtSignal(str)
    ble_scan_post = pyqtSignal(int)
    ble_session_pre = pyqtSignal(str, int, int)
    ble_session_post = pyqtSignal(str)
    ble_logger_pre = pyqtSignal()
    ble_logger_post = pyqtSignal(bool, str, str)
    ble_logger_plot_req = pyqtSignal(str)
    ble_file_pre = pyqtSignal(str, int, int, int, int)
    ble_file_post = pyqtSignal(int)
    ble_deployed = pyqtSignal(str, str, str)
    ble_status = pyqtSignal(str)
    ble_debug = pyqtSignal(str)
    ble_error = pyqtSignal(str)
    ble_dl_warning = pyqtSignal(list)
    ble_dl_step = pyqtSignal()


class SignalsGPS(QObject):
    gps_status = pyqtSignal(str)
    gps_error = pyqtSignal(str)
    gps_update_time_via = pyqtSignal(str)
    gps_update_pos = pyqtSignal(str, str)


class SignalsFTP(QObject):
    ftp_update = pyqtSignal(str)
    ftp_status = pyqtSignal(str)
    ftp_error = pyqtSignal(str)


class SignalsPLT(QObject):
    plt_status = pyqtSignal(str)
    plt_start = pyqtSignal()
    plt_result = pyqtSignal(object, str)
    plt_msg = pyqtSignal(str)
    plt_error = pyqtSignal(str)


class SignalsTime(QObject):
    time_update = pyqtSignal(str)
    time_status = pyqtSignal(str)


class SignalsNET(QObject):
    net_status = pyqtSignal(str)
    net_update = pyqtSignal(str)


class SignalsCNV(QObject):
    cnv_status = pyqtSignal(str)
    cnv_error = pyqtSignal(str)
    cnv_update = pyqtSignal(list)

