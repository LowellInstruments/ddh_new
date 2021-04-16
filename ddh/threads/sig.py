from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject


class SignalsBLE(QObject):
    status = pyqtSignal(str)
    debug = pyqtSignal(str)
    error = pyqtSignal(str)
    scan_pre = pyqtSignal(str)

    logger_dl_start = pyqtSignal(str)
    logger_dl_start_file = pyqtSignal(str, int, int, int, int)
    logger_dl_progress_get_file = pyqtSignal()
    logger_dl_progress_dwg_file = pyqtSignal()
    logger_dl_end = pyqtSignal(bool, str, str)

    logger_plot_req = pyqtSignal(str)
    logger_deployed = pyqtSignal(str, str, str)
    logger_gps_nope = pyqtSignal(str)
    logger_to_orange = pyqtSignal(list)


class SignalsGPS(QObject):
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    update = pyqtSignal(object)
    debug = pyqtSignal(str)


class SignalsAWS(QObject):
    update = pyqtSignal(str)
    status = pyqtSignal(str)
    error = pyqtSignal(str)


class SignalsBoot(QObject):
    status = pyqtSignal(str)
    error = pyqtSignal(str)


class SignalsPLT(QObject):
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    update = pyqtSignal(str)
    start = pyqtSignal()
    end = pyqtSignal(object, str)
    msg = pyqtSignal(str)
    debug = pyqtSignal(str)


class SignalsTime(QObject):
    status = pyqtSignal(str)
    update = pyqtSignal(str)
    via = pyqtSignal(str)


class SignalsNET(QObject):
    status = pyqtSignal(str)
    update = pyqtSignal(str)


class SignalsCNV(QObject):
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    update = pyqtSignal(list)
    debug = pyqtSignal(str)
