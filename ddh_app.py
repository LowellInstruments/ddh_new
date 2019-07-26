import datetime, sys, time
from gui.ble_gui_ui import Ui_tabs
from PyQt5.QtCore import Qt, QThreadPool, pyqtSlot
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QMainWindow,
    QApplication,
    QTabWidget,
    QDesktopWidget,
)
from apps.ddh_threads import DDHThread
from apps.ddh_gps import DeckDataHubGPS
from apps.ddh_ble import DeckDataHubBLE
from apps.ddh_plt import DeckDataHubPLT, StaticCanvas
from apps.ddh_gui import DeckDataHubGUI, ButtonPressEvent
from apps.ddh_utils import (
    update_dl_folder_list,
    detect_raspberry,
    check_config_file,
    get_ship_name
)
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


# application behavior constants
DDH_BLE_MAC_FILTER = (
    # remember : separator, not -
    '00:1e:c0:4d:bf:c9',
    '00:1e:c0:4d:d2:37',
    '00:1e:c0:4d:bf:db'
)
DDH_GPS_PERIOD = 10
DDH_PLT_DISPLAY_PERIOD = 30
DDH_ERR_DISPLAY_PERIOD = 10
# DDH_CLK_START_TIME = 0


# main code
class DDHQtApp(QMainWindow):

    # application behavior variables
    btn_1_held = 0

    def __init__(self, *args, **kwargs):
        # checks
        singleton.SingleInstance()
        assert sys.version_info >= (3, 5)
        assert check_config_file()

        # ui stuff
        super(DDHQtApp, self).__init__(*args, **kwargs)
        self.tabs = QTabWidget()
        self.ui = Ui_tabs()
        self.ui.setupUi(self.tabs)
        self.setWindowTitle('Lowell Instruments\' Deck Data Hub')
        self.ui.lbl_error.hide()
        self.ui.lbl_busy_dl.hide()
        self.ui.lbl_busy_plot.hide()
        self.ui.img_time.setPixmap(QPixmap('gui/res/img_datetime.png'))
        self.ui.img_sync.setPixmap(QPixmap('gui/res/img_sync.png'))
        self.ui.img_boat.setPixmap(QPixmap('gui/res/img_boatname.png'))
        self.tabs.setTabIcon(0, QIcon('gui/res/icon_info.ico'))
        self.tabs.setTabIcon(1, QIcon('gui/res/icon_dl.ico'))
        self.tabs.setTabIcon(2, QIcon('gui/res/icon_graph.ico'))
        self.setWindowIcon(QIcon('gui/res/icon_lowell.ico'))
        self.ui.lbl_boatname.setText(get_ship_name())
        self.setCentralWidget(self.tabs)
        self.tabs.setCurrentIndex(0)
        self._window_center()
        self.plot_canvas = StaticCanvas()
        self.ui.vl_3.addWidget(self.plot_canvas)

        # automatic flow stuff
        self.sys_seconds = 0
        self.dl_last_dir = ''
        self.bsy_indicator = ''
        self.plt_timeout_display = 0
        self.err_timeout_display = 0
        self.plt_folders = update_dl_folder_list()
        self.plt_folders_idx = 0
        self.plt_dir_1 = None
        self.plt_dir_2 = None
        self.plt_time_spans = ('hour', 'day', 'week', 'month', 'year')
        self.plt_ts_idx = 0
        self.plt_ts = self.plt_time_spans[0]

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

            def button3_pressed_cb():
                self.keyPressEvent(ButtonPressEvent(Qt.Key_3))

            # def button1_released_cb():
            #     print('released button 1')
            #     if DDHQtApp.btn_1_held:
            #         self.keyPressEvent(ButtonPressEvent(Qt.Key_4))
            #     else:
            #         self.keyPressEvent(ButtonPressEvent(Qt.Key_1))
            #     DDHQtApp.btn_1_held = 0
            #
            # def button1_held_cb():
            #     DDHQtApp.btn_1_held = 1
            #     print('held button 1')

            # raspberry button creation
            self.button1 = Button(26, pull_up=True)
            self.button2 = Button(19, pull_up=True)
            self.button3 = Button(13, pull_up=True)
            # self.button1.when_held = button1_held_cb
            # self.button1.when_released = button1_released_cb
            self.button1.when_pressed = button1_pressed_cb
            self.button2.when_pressed = button2_pressed_cb
            self.button3.when_pressed = button3_pressed_cb

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
        fxn = DeckDataHubGPS.gps_loop
        self.th_gps = DDHThread(fxn, SignalsGPS, DDH_GPS_PERIOD)
        self.th_gps.signals.status.connect(self.slot_status)
        self.th_gps.signals.error.connect(self.slot_error)
        self.th_gps.signals.gps_result.connect(self.slot_gps_result)

    def _ddh_thread_throw_plt(self, folders_to_plot):
        fxn = DeckDataHubPLT.plt_plot
        args_th_plt = [folders_to_plot, self.plot_canvas, self.plt_ts]
        self.th_plt = DDHThread(fxn, SignalsPLT, *args_th_plt)
        self.th_plt.signals.status.connect(self.slot_status)
        self.th_plt.signals.debug.connect(self.slot_debug)
        self.th_plt.signals.error.connect(self.slot_error)
        self.th_plt.signals.error_gui.connect(self.slot_error_gui)
        self.th_plt.signals.plt_result.connect(self.slot_plt_result)
        self.th_plt.signals.clk_start.connect(self.slot_clk_start)
        self.th_plt.signals.clk_end.connect(self.slot_clk_end)
        self.th_plt.signals.status_gui.connect(self.slot_status_gui)
        self.th_plt.signals.status_gui_clear.connect(self.slot_status_gui_clear)
        self.thread_pool.start(self.th_plt)

    def _window_center(self):
        if detect_raspberry():
            # in raspberry, use full screen on production code
            # self.showFullScreen()
            self.setFixedSize(self.tabs.size())
        else:
            # make window as big as tabs widget
            self.setFixedSize(self.tabs.size())

        # get window and screen shape, match both, adjust upper left corner
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
            self.plt_dir_1 = self.plt_folders[self.plt_folders_idx]
        elif e.key() == Qt.Key_2:
            console_log.debug('GUI: keypress 2.')
            self.plt_folders_idx += 1
            self.plt_folders_idx %= len(self.plt_folders)
            self.plt_dir_2 = self.plt_folders[self.plt_folders_idx]
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
        if self.plt_dir_1 and self.plt_dir_1 == self.plt_dir_2:
            self.plt_dir_2 = None
        folders_to_plot = [self.plt_dir_1, self.plt_dir_2]
        self._ddh_thread_throw_plt(folders_to_plot)

    @pyqtSlot(name='slot_ble_scan_start')
    def slot_ble_scan_start(self):
        self.ui.lbl_busy_dl.hide()
        self.ui.lbl_dl_status_1.clear()
        self.ui.lbl_dl_status_2.clear()
        self.ui.lbl_dl_status_3.clear()
        self.ui.bar_dl.setValue(0)
        self.ui.lbl_dl_status_1.setText('Scanning for loggers...\n\n\n')

    @pyqtSlot(object, name='slot_ble_scan_result')
    def slot_ble_scan_result(self, result):
        if result:
            self.tabs.setCurrentIndex(1)
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
        self.ui.lbl_error.setText(t)
        self.ui.lbl_error.setStyleSheet(style)
        self.err_timeout_display = DDH_ERR_DISPLAY_PERIOD
        self.ui.lbl_error.show()

    @pyqtSlot(str, name='slot_error')
    def slot_error(self, e):
        console_log.error(e)

    @pyqtSlot(str, name='slot_error_gui')
    def slot_error_gui(self, e):
        console_log.error(e)

        # google: stylesheet named colors
        style = "background-color: LightBlue; border-style: outset;"
        style += "border-width: 2px; border-radius: 10px;"
        self.ui.lbl_error.setText(e)
        self.ui.lbl_error.setStyleSheet(style)
        self.err_timeout_display = DDH_ERR_DISPLAY_PERIOD
        self.ui.lbl_error.show()

    # a download session consists of 1 to n loggers
    @pyqtSlot(str, int, int, name='slot_ble_dl_session')
    def slot_ble_dl_session(self, desc, val_1, val_2):
        text = 'Connected {}\n\nLogger {} of {}'.format(desc, val_1, val_2)
        self.ui.lbl_dl_status_1.setText(text)
        self.ui.lbl_busy_dl.show()
        self.ui.bar_dl.setValue(0)

    @pyqtSlot(name='slot_ble_dl_logger')
    def slot_ble_dl_logger(self):
        text = '\nConfiguring logger for download...'
        self.ui.lbl_dl_status_2.setText(text)

    # one logger can have 1 to n files
    @pyqtSlot(str, int, int, int, name='slot_ble_dl_file')
    def slot_ble_dl_file(self, desc, val_1, val_2, val_3):
        text = '\nGetting file {} of {} -> {}'.format(val_1, val_2, desc)
        text += '\n\n{} minutes to full logger download'.format(val_3)
        self.ui.lbl_dl_status_2.setText(text)

    @pyqtSlot(int, int, name='slot_ble_dl_file_')
    def slot_ble_dl_file_(self, val_1, val_2):
        text = '{} bytes/sec'.format(val_2)
        percentage = self.ui.bar_dl.value() + val_1
        self.ui.lbl_dl_status_3.setText('\n{}'.format(text))
        self.ui.bar_dl.setValue(percentage)

    @pyqtSlot(str, int, name='slot_ble_dl_logger_')
    def slot_ble_dl_logger_(self, desc, val_1):
        text = 'Logger {} sent {} files.'.format(desc, val_1)
        self.ui.lbl_dl_status_1.setText(text)
        self.ui.lbl_dl_status_2.clear()
        self.ui.lbl_dl_status_3.clear()
        self.ui.bar_dl.setValue(100)
        # try to draw if something downloaded from last logger
        if val_1:
            DeckDataHubPLT.plt_cache_clear()
            self.dl_last_dir = 'dl_files/' + str(desc).replace(':', '-')
            self.plt_folders = [self.dl_last_dir, None]
            self._ddh_thread_throw_plt(self.plt_folders)

    @pyqtSlot(object, name='slot_plt_result')
    def slot_plt_result(self, result):
        if result:
            self.tabs.setCurrentIndex(2)
            self.plt_timeout_display = DDH_PLT_DISPLAY_PERIOD
        else:
            self.tabs.setCurrentIndex(0)

    @pyqtSlot(str, name='slot_ble_dl_session_')
    def slot_ble_dl_session_(self, desc):
        console_log.info(desc)

    @pyqtSlot(str, str, str, str, name='slot_gps_result')
    def slot_gps_result(self, clk_source, gps_time, gps_lat, gps_lon):
        self.ui.lbl_sync.setText(clk_source + ' clock sync')
        if clk_source == 'gps':
            t = 'GPS: received RMC frame.\n'
            t += '\t-> {} US/Eastern time offset adjusted.\n'.format(gps_time)
            t += '\t-> lat {} lon {}.'.format(gps_lat, gps_lon)
            console_log.info(t)

    @pyqtSlot(str, name='slot_gui_tick')
    def slot_gui_tick(self, desc):
        # update some widgets in GUI
        self.sys_seconds += 1
        self.bsy_indicator = desc
        time_format = '\n%m / %d / %y\n%H : %M : %S'
        formatted_time = datetime.datetime.now().strftime(time_format)
        self.ui.lbl_time.setText(formatted_time)
        self.ui.lbl_busy_dl.setText(self.bsy_indicator)
        self.ui.lbl_busy_plot.setText(self.bsy_indicator)

        # timeout to display plot tab, compare to 1 only runs once
        if self.plt_timeout_display == 1:
            self.tabs.setCurrentIndex(0)
        if self.plt_timeout_display > 0:
            self.plt_timeout_display -= 1

        # timeout to display error banner, compare to 1 only runs once
        if self.err_timeout_display == 1:
            self.ui.lbl_error.hide()
        if self.err_timeout_display > 0:
            self.err_timeout_display -= 1

        # things updated less often
        if self.sys_seconds % 30 == 0:
            self.ui.lbl_boatname.setText(get_ship_name())

    @pyqtSlot(name='slot_clk_start')
    def slot_clk_start(self):
        # todo: fix this global variable thing naming
        DDHQtApp.DDH_CLK_START_TIME = time.clock()

    @pyqtSlot(name='slot_status_gui_clear')
    def slot_status_gui_clear(self):
        self.ui.lbl_error.hide()

    @pyqtSlot(name='slot_clk_end')
    def slot_clk_end(self):
        start_time = DDHQtApp.DDH_CLK_START_TIME
        elapsed_time = int((time.clock() - start_time) * 1000)
        text = 'SYS: elapsed time {} ms.'.format(elapsed_time)
        console_log.debug(text)


def run_app():
    app = QApplication(sys.argv)
    ex = DDHQtApp()
    ex.show()
    sys.exit(app.exec_())
