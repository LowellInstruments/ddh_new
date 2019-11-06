import datetime
import sys
import time
import os
import signal
from gui.ble_gui import Ui_tabs
from PyQt5.QtCore import (
    Qt,
    QThreadPool,
    pyqtSlot
)
from PyQt5.QtGui import (
    QIcon,
    QPixmap
)
from PyQt5.QtWidgets import (
    QMainWindow,
    QApplication,
    QTabWidget,
    QDesktopWidget,
)
from apps.ddh_threads import DDHThread
from apps.ddh_gps import DeckDataHubGPS
from apps.ddh_ble import DeckDataHubBLE
from apps.ddh_plt import DeckDataHubPLT
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from apps.ddh_gui import DeckDataHubGUI, ButtonPressEvent
from apps.ddh_utils import (
    update_dl_folder_list,
    detect_raspberry,
    check_config_file,
    get_ship_name,
    get_metrics,
    linux_set_time_to_use_ntp,
    get_mac_filter,
    mac_dns
)
import logzero
from logzero import logger as console_log
from tendo import singleton
from apps.ddh_signals import (
    SignalsBLE,
    SignalsGPS,
    SignalsPLT,
    SignalsGUI,
)
if detect_raspberry():
    from gpiozero import Button


# constants for the application
DDH_BLE_MAC_FILTER = get_mac_filter()
DDH_ERR_DISPLAY_TIMEOUT = 5
DDH_PLT_DISPLAY_TIMEOUT = 25
DDH_GPS_PERIOD = 30


# main code
class DDHQtApp(QMainWindow):

    # application behavior variables
    btn_3_held = 0
    clk_start_time = None

    def __init__(self, *args, **kwargs):
        # checks
        singleton.SingleInstance()
        assert sys.version_info >= (3, 5)
        assert check_config_file()
        if os.path.exists('ddh_avg.db'):
            os.remove('ddh_avg.db')
        logzero.logfile("ddh.log", maxBytes=int(1e6), backupCount=3, mode='a')

        # banners
        console_log.debug('SYS: recall \'rm_previous\' pre_dl, search \'***\'')
        console_log.debug('SYS: recall re-RUN post download, search \'###\'')

        # ui stuff
        super(DDHQtApp, self).__init__(*args, **kwargs)
        self.tabs = QTabWidget()
        self.ui = Ui_tabs()
        self.ui.setupUi(self.tabs)
        self.setWindowTitle('Lowell Instruments\' Deck Data Hub')
        # self.ui.lbl_error.hide()
        # self.ui.lbl_busy_dl.hide()
        self.ui.lbl_busy_plot.hide()
        self.ui.img_time.setPixmap(QPixmap('gui/res/img_datetime.png'))
        self.ui.img_sync.setPixmap(QPixmap('gui/res/img_sync.png'))
        self.ui.img_boat.setPixmap(QPixmap('gui/res/img_boatname.png'))
        self.ui.img_ble.setPixmap(QPixmap('gui/res/img_blue.png'))
        self.ui.img_latnlon.setPixmap(QPixmap('gui/res/img_latnlon.png'))
        self.ui.img_time.setPixmap(QPixmap('gui/res/img_datetime_color.png'))
        self.ui.img_sync.setPixmap(QPixmap('gui/res/img_sync_color.png'))
        self.ui.img_boat.setPixmap(QPixmap('gui/res/img_boatname_color.png'))
        self.ui.img_ble.setPixmap(QPixmap('gui/res/img_blue_color.png'))
        self.ui.img_latnlon.setPixmap(QPixmap('gui/res/img_latnlon_color.png'))
        self.ui.img_output.setPixmap(QPixmap('gui/res/img_wait_color.png'))
        self.tabs.setTabIcon(0, QIcon('gui/res/icon_info.png'))
        self.tabs.setTabIcon(1, QIcon('gui/res/icon_graph.ico'))
        self.tabs.setTabIcon(2, QIcon('gui/res/icon_history.ico'))
        self.setWindowIcon(QIcon('gui/res/icon_lowell.ico'))
        self.ui.lbl_boatname.setText(get_ship_name())
        self.setCentralWidget(self.tabs)
        self.tabs.setCurrentIndex(0)
        self._window_center()
        self.plot_canvas = FigureCanvasQTAgg(Figure(figsize=(5, 3)))
        self.ui.vl_3.addWidget(self.plot_canvas)

        # automatic flow stuff
        self.sys_seconds = 0
        self.dl_last_dir = ''
        self.bsy_indicator = ''
        self.plt_timeout_display = 0
        self.err_timeout_display = 0
        self.plt_folders = update_dl_folder_list()
        self.plt_folders_idx = 0
        self.plt_dir = None
        self.plt_time_spans = ('h', 'd', 'w', 'm', 'y')
        self.plt_ts_idx = 0
        self.plt_ts = self.plt_time_spans[0]
        self.plt_metrics = get_metrics()
        self.plt_metrics_idx = 0
        self.plt_metric = self.plt_metrics[0]
        self.plt_is_busy = False

        # threads
        self.th_ble = None
        self.th_gps = None
        self.th_plt = None
        self.th_gui = None
        self.thread_pool = QThreadPool()
        self._ddh_threads_create()
        self.thread_pool.start(self.th_gui)
        self.thread_pool.start(self.th_ble)
        self.thread_pool.start(self.th_gps)
        # do not boot a thread plot

        # particular hardware stuff
        if detect_raspberry():
            def button1_pressed_cb():
                self.keyPressEvent(ButtonPressEvent(Qt.Key_1))

            def button2_pressed_cb():
                self.keyPressEvent(ButtonPressEvent(Qt.Key_2))

            # upon release, check if it was a press or a hold
            def button3_released_cb():
                if DDHQtApp.btn_3_held:
                    self.keyPressEvent(ButtonPressEvent(Qt.Key_6))
                else:
                    self.keyPressEvent(ButtonPressEvent(Qt.Key_3))
                DDHQtApp.btn_3_held = 0

            def button3_held_cb():
                DDHQtApp.btn_3_held = 1

            self.button1 = Button(26, pull_up=True)
            self.button2 = Button(19, pull_up=True)
            self.button3 = Button(13, pull_up=True)
            self.button1.when_pressed = button1_pressed_cb
            self.button2.when_pressed = button2_pressed_cb
            # a more featured button
            self.button3.when_held = button3_held_cb
            self.button3.when_released = button3_released_cb

        else:
            console_log.debug('SYS: this is NOT a raspberry system')

    def closeEvent(self, event):
        console_log.debug('SYS: closing GUI APP...')
        linux_set_time_to_use_ntp()
        event.accept()

    def _ddh_threads_create(self):
        # threads: creation
        fxn = DeckDataHubGUI.gui_loop
        self.th_gui = DDHThread(fxn, SignalsGUI)
        self.th_gui.signals.gui_tick.connect(self.slot_gui_tick)
        fxn = DeckDataHubBLE.ble_loop
        self.th_ble = DDHThread(fxn, SignalsBLE, DDH_BLE_MAC_FILTER)
        self.th_ble.signals.ble_scan_start.connect(self.slot_ble_scan_start)
        self.th_ble.signals.ble_scan_result.connect(self.slot_ble_scan_result)
        self.th_ble.signals.ble_dl_session.connect(self.slot_ble_dl_session)
        self.th_ble.signals.ble_dl_session_.connect(self.slot_ble_dl_session_)
        self.th_ble.signals.ble_dl_logger.connect(self.slot_ble_dl_logger)
        self.th_ble.signals.ble_dl_logger_.connect(self.slot_ble_dl_logger_)
        self.th_ble.signals.ble_dl_file.connect(self.slot_ble_dl_file)
        self.th_ble.signals.ble_dl_file_.connect(self.slot_ble_dl_file_)
        self.th_ble.signals.status.connect(self.slot_status)
        self.th_ble.signals.error.connect(self.slot_error)
        self.th_ble.signals.output.connect(self.slot_output)
        self.th_ble.signals.warning.connect(self.slot_warning)
        fxn = DeckDataHubGPS.gps_loop
        self.th_gps = DDHThread(fxn, SignalsGPS, DDH_GPS_PERIOD)
        self.th_gps.signals.status.connect(self.slot_status)
        self.th_gps.signals.error.connect(self.slot_error)
        self.th_gps.signals.gps_result.connect(self.slot_gps_result)
        self.th_gps.signals.internet_result.connect(self.slot_internet_result)
        self.th_gps.signals.gps_update.connect(self.slot_gps_update)

    def _ddh_thread_throw_plt(self, folder_to_plot):
        fxn = DeckDataHubPLT.plt_plot
        a = [folder_to_plot, self.plot_canvas, self.plt_ts, self.plt_metric]
        self.th_plt = DDHThread(fxn, SignalsPLT, *a)
        self.th_plt.signals.status.connect(self.slot_status)
        self.th_plt.signals.debug.connect(self.slot_debug)
        self.th_plt.signals.error.connect(self.slot_error)
        self.th_plt.signals.error_gui.connect(self.slot_error_gui)
        self.th_plt.signals.plt_result.connect(self.slot_plt_result)
        self.th_plt.signals.clk_start.connect(self.slot_clk_start)
        self.th_plt.signals.clk_end.connect(self.slot_clk_end)
        self.th_plt.signals.status_gui.connect(self.slot_status_gui)
        self.thread_pool.start(self.th_plt)

    def _window_center(self):
        if detect_raspberry():
            # in raspberry, use full screen on production code
            # self.showFullScreen()
            self.setFixedSize(self.tabs.size())
        else:
            # make window as big as tabs widget
            self.setFixedSize(self.tabs.size())

        # get window + screen shape, match both, adjust upper left corner
        rectangle = self.frameGeometry()
        point_center_screen = QDesktopWidget().availableGeometry().center()
        rectangle.moveCenter(point_center_screen)
        self.move(rectangle.topLeft())

    def keyPressEvent(self, e):
        # emulate raspberry button presses, no holds
        if e.key() == Qt.Key_1:
            console_log.debug('GUI: keypress 1.')
            self.plt_folders_idx += 1
            self.plt_folders_idx %= len(self.plt_folders)
            self.plt_dir = self.plt_folders[self.plt_folders_idx]
        elif e.key() == Qt.Key_2:
            console_log.debug('GUI: keypress 2.')
            self.plt_metrics_idx += 1
            self.plt_metrics_idx %= len(self.plt_metrics)
            self.plt_metric = self.plt_metrics[self.plt_metrics_idx]
        elif e.key() == Qt.Key_3:
            self.plt_ts_idx += 1
            self.plt_ts_idx %= len(self.plt_time_spans)
            self.plt_ts = self.plt_time_spans[self.plt_ts_idx]
            console_log.debug('GUI: keypress 3.')
        # emulate raspberry button holds
        elif e.key() == Qt.Key_4:
            console_log.debug('GUI: keypress 4.')
        elif e.key() == Qt.Key_5:
            console_log.debug('GUI: keypress 5.')
        elif e.key() == Qt.Key_6:
            console_log.debug('GUI: keypress 6.')
        else:
            console_log.debug('GUI: keypress unknown.')
            return

        # logic checks and do the thing
        if not self.plt_dir:
            console_log.debug('GUI: no folder to plot')
            return

        if not self.plt_is_busy:
            self.plt_is_busy = True
            self._ddh_thread_throw_plt(self.plt_dir)
        else:
            console_log.debug('GUI: busy to plot')

    @pyqtSlot(name='slot_ble_scan_start')
    def slot_ble_scan_start(self):
        self.ui.bar_dl.setValue(0)
        self.ui.lbl_ble_short.setText('Scanning ...')

    @pyqtSlot(object, name='slot_ble_scan_result')
    def slot_ble_scan_result(self, result):
        # do nothing, wherever we are
        if result:
            pass
        else:
            pass

    @pyqtSlot(str, name='slot_status')
    def slot_status(self, t):
        console_log.info(t)

    @pyqtSlot(str, name='slot_debug')
    def slot_debug(self, t):
        console_log.debug(t)

    @pyqtSlot(str, name='slot_status_gui')
    def slot_status_gui(self, t):
        console_log.info(t)

        # google: stylesheet named colors
        style = "background-color: LightYellow; border-style: outset;"
        style += "border-width: 2px; border-radius: 10px;"
        # self.ui.lbl_error.setText(t)
        # self.ui.lbl_error.setStyleSheet(style)
        self.err_timeout_display = DDH_ERR_DISPLAY_TIMEOUT
        # self.ui.lbl_error.show()

    @pyqtSlot(str, name='slot_error')
    def slot_error(self, e):
        console_log.error(e)

    @pyqtSlot(str, name='slot_warning')
    def slot_warning(self, e):
        console_log.warning(e)

    @pyqtSlot(str, name='slot_error_gui')
    def slot_error_gui(self, e):
        console_log.error(e)
        self.tabs.setCurrentIndex(0)

        # google: stylesheet named colors
        style = "background-color: LightBlue; border-style: outset;"
        style += "border-width: 2px; border-radius: 10px;"
        # self.ui.lbl_error.setText(e)
        # self.ui.lbl_error.setStyleSheet(style)
        self.err_timeout_display = DDH_ERR_DISPLAY_TIMEOUT
        # self.ui.lbl_error.show()

    # a download session consists of 1 to n loggers
    @pyqtSlot(str, int, int, name='slot_ble_dl_session')
    def slot_ble_dl_session(self, desc, val_1, val_2):
        # desc: name, val_1: logger index, val_2: total num of loggers
        text = 'Connected'
        self.ui.lbl_ble_short.setText(text)
        text = 'Logger \n{}'.format(mac_dns(desc))
        self.ui.lbl_output.setText(text)
        self.ui.bar_dl.setValue(0)

    # indicates current logger of current download session
    @pyqtSlot(name='slot_ble_dl_logger')
    def slot_ble_dl_logger(self):
        text = 'Configuring'
        self.ui.lbl_ble_short.setText(text)

    # one logger can have 1 to n files
    @pyqtSlot(str, int, int, int, name='slot_ble_dl_file')
    def slot_ble_dl_file(self, desc, val_1, val_2, val_3):
        # val_1: file index, val_2: total files, desc: file name
        text = 'Downloading'
        self.ui.lbl_ble_short.setText(text)
        text = '{} minutes left'.format(val_3)
        self.ui.lbl_output.setText(text)

    # function post dl_file, note trailing '_'
    @pyqtSlot(int, int, name='slot_ble_dl_file_')
    def slot_ble_dl_file_(self, val_1, val_2):
        # val_1: percentage increase, val_2: data rate
        text = '{} B/s'.format(val_2)
        self.ui.lbl_output.setText(text)
        percentage = self.ui.bar_dl.value() + val_1
        self.ui.bar_dl.setValue(percentage)

    # function post dl_logger, note trailing '_'
    @pyqtSlot(str, int, name='slot_ble_dl_logger_')
    def slot_ble_dl_logger_(self, desc, val_1):
        # desc: logger name, val_1: number of files sent
        text = 'Completed'
        self.ui.lbl_ble_short.setText(text)
        text = 'Got {} files'.format(val_1)
        self.ui.lbl_output.setText(text)
        self.ui.bar_dl.setValue(100)
        # try to draw if something downloaded from last logger
        if val_1:
            self.dl_last_dir = 'dl_files/' + str(desc).replace(':', '-')
            self._ddh_thread_throw_plt(self.dl_last_dir)
            self.plt_folders = update_dl_folder_list()

    # display plot if we were successful
    @pyqtSlot(object, name='slot_plt_result')
    def slot_plt_result(self, result):
        if result:
            self.tabs.setCurrentIndex(1)
            self.plt_timeout_display = DDH_PLT_DISPLAY_TIMEOUT
        else:
            self.tabs.setCurrentIndex(0)
        self.plt_is_busy = False

    # function post dl_session, note trailing '_'
    @pyqtSlot(str, name='slot_ble_dl_session_')
    def slot_ble_dl_session_(self, desc):
        console_log.info(desc)

    @pyqtSlot(str, str, str, str, name='slot_gps_result')
    def slot_gps_result(self, clk_source, gps_time, gps_lat, gps_lon):
        self.ui.lbl_clock_sync.setText(clk_source + ' time')
        if clk_source == 'gps':
            t = 'GPS: received RMC frame.\n'
            t += '\t-> {} US/Eastern time offset adjusted.\n'.format(gps_time)
            t += '\t-> lat {} lon {}.'.format(gps_lat, gps_lon)
            console_log.info(t)

    @pyqtSlot(bool, str, str, name='slot_gps_update')
    def slot_gps_update(self, did_ok, gps_lat, gps_lon):
        if did_ok:
            self.ui.lbl_gps.setText(gps_lat + ' N\n' + gps_lon + ' W')
            t = 'GPS: updated pos lat, lon'.format(gps_lat, gps_lon)
        else:
            # ugly and piggybacked GPS error message
            self.ui.lbl_gps.setText(gps_lat)
            t = 'GPS: no position update'
        console_log.info(t)

    @pyqtSlot(bool, str, name='slot_internet_result')
    def slot_internet_result(self, we_have, internet_source):
        if we_have:
            self.ui.lbl_internet.setText('Internet\nconnected')
            t = 'SYS: we have internet'
        else:
            self.ui.lbl_internet.setText('Internet\ndisconnected')
            t = 'SYS: NO internet connection detected'
        console_log.info(t)

    @pyqtSlot(str, name='slot_gui_tick')
    def slot_gui_tick(self, desc):
        # update some widgets in GUI
        self.sys_seconds += 1
        self.bsy_indicator = desc
        time_format = '%m / %d / %y\n%H : %M : %S'
        formatted_time = datetime.datetime.now().strftime(time_format)
        self.ui.lbl_clock_time.setText(formatted_time)
        # self.ui.lbl_busy_dl.setText(self.bsy_indicator)
        self.ui.lbl_busy_plot.setText(self.bsy_indicator)

        # timeout to display plot tab, compare to 1 only runs once
        if self.plt_timeout_display == 1:
            self.tabs.setCurrentIndex(0)
        if self.plt_timeout_display > 0:
            self.plt_timeout_display -= 1

        # timeout to display error banner, compare to 1 only runs once
        # if self.err_timeout_display == 1:
        #     self.ui.lbl_error.hide()
        if self.err_timeout_display > 0:
            self.err_timeout_display -= 1

        # things updated less often
        if self.sys_seconds % 30 == 0:
            self.ui.lbl_boatname.setText(get_ship_name())

    @pyqtSlot(name='slot_clk_start')
    def slot_clk_start(self):
        self.clk_start_time = time.clock()

    @pyqtSlot(name='slot_clk_end')
    def slot_clk_end(self):
        elapsed_time = int((time.clock() - self.clk_start_time) * 1000)
        text = 'SYS: elapsed time {} ms.'.format(elapsed_time)
        console_log.debug(text)

    @pyqtSlot(str, name='slot_output')
    def slot_output(self, desc):
        self.ui.lbl_output.setText(desc)


def run_app():
    # catch control + c
    signal.signal(signal.SIGINT, on_ctrl_c)
    app = QApplication(sys.argv)
    ex = DDHQtApp()
    ex.show()
    sys.exit(app.exec_())


def on_ctrl_c(signal_num, _):
    console_log.debug('SYS: captured signal {}...'.format(signal_num))
    linux_set_time_to_use_ntp()
    sys.exit(signal_num)
