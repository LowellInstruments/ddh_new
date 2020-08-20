from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject


class SignalsBLE(QObject):
    ble_scan_pre = pyqtSignal(str)
    ble_scan_post = pyqtSignal(object)
    ble_session_pre = pyqtSignal(str, int, int)
    ble_session_post = pyqtSignal(str)
    ble_logger_pre = pyqtSignal()
    ble_logger_post = pyqtSignal(int)
    ble_logger_plot_req = pyqtSignal(str)
    ble_file_pre = pyqtSignal(str, int, int, int, int)
    ble_file_post = pyqtSignal(int, int)
    ble_deployed = pyqtSignal(str, str, str)
    ble_error = pyqtSignal(str)
    ble_status = pyqtSignal(str)
    ble_warning = pyqtSignal(str)
    ble_output = pyqtSignal(str)
    ble_dl_step = pyqtSignal()


class SignalsGPS(QObject):
    gps_status = pyqtSignal(str)
    gps_error = pyqtSignal(str)
    gps_result = pyqtSignal(str, str, str, str)
    gps_update = pyqtSignal(bool, str, str)


class SignalsFTP(QObject):
    ftp_conn = pyqtSignal(str)
    ftp_status = pyqtSignal(str)
    ftp_error = pyqtSignal(str)


class SignalsPLT(QObject):
    plt_status = pyqtSignal(str)
    plt_start = pyqtSignal()
    plt_result = pyqtSignal(object)
    plt_msg = pyqtSignal(str)
    plt_error = pyqtSignal(str)


class SignalsLife(QObject):
    lif_beat = pyqtSignal(str)
    lif_status = pyqtSignal(str)


class SignalsNET(QObject):
    net_status = pyqtSignal(str)
    net_rv = pyqtSignal(str)


class SignalsCNV(QObject):
    cnv_status = pyqtSignal(str)
    cnv_error = pyqtSignal(str)
