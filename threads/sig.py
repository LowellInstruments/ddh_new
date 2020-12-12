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
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    update = pyqtSignal(tuple)


class SignalsFTP(QObject):
    ftp_update = pyqtSignal(str)
    ftp_status = pyqtSignal(str)
    ftp_error = pyqtSignal(str)


class SignalsPLT(QObject):
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    update = pyqtSignal(str)
    start = pyqtSignal()
    end = pyqtSignal(object, str)
    msg = pyqtSignal(str)


class SignalsTime(QObject):
    update = pyqtSignal(str)


class SignalsNET(QObject):
    status = pyqtSignal(str)
    update = pyqtSignal(str)


class SignalsCNV(QObject):
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    update = pyqtSignal(list)

