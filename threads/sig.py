from PyQt5.QtCore import pyqtSignal
from PyQt5.QtCore import QObject


class SignalsBLE(QObject):
    scan_pre = pyqtSignal(str)
    scan_post = pyqtSignal(int)
    session_pre = pyqtSignal(str, int, int)
    session_post = pyqtSignal(str)
    logger_pre = pyqtSignal()
    logger_post = pyqtSignal(bool, str, str)
    logger_plot_req = pyqtSignal(str)
    file_pre = pyqtSignal(str, int, int, int, int)
    file_post = pyqtSignal(int)
    deployed = pyqtSignal(str, str, str)
    status = pyqtSignal(str)
    debug = pyqtSignal(str)
    error = pyqtSignal(str)
    dl_warning = pyqtSignal(list)
    dl_step = pyqtSignal()


class SignalsGPS(QObject):
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    update = pyqtSignal(tuple)


class SignalsFTP(QObject):
    update = pyqtSignal(str)
    status = pyqtSignal(str)
    error = pyqtSignal(str)


class SignalsAWS(QObject):
    update = pyqtSignal(str)
    status = pyqtSignal(str)
    error = pyqtSignal(str)


class SignalsPLT(QObject):
    status = pyqtSignal(str)
    error = pyqtSignal(str)
    update = pyqtSignal(str)
    start = pyqtSignal()
    end = pyqtSignal(object, str)
    msg = pyqtSignal(str)


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

