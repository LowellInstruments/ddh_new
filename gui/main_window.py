import time
import matplotlib
from mat.linux import linux_is_rpi
from threads.utils_ftp import ftp_assert_credentials
matplotlib.use('Qt5Agg')
import datetime
import pathlib
import shutil
import sys
from settings import ctx
from PyQt5.QtCore import (
    Qt,
    QThreadPool,
    pyqtSlot,
    QTimer)
from PyQt5.QtGui import (
    QPixmap,
    QIcon)
from PyQt5.QtWidgets import (
    QMainWindow,
    QFileDialog, QApplication)

from gui import utils_gui
from gui.utils_gui import (
    setup_view, setup_his_tab, setup_buttons_gui, setup_window_center, hide_edit_tab,
    dict_from_list_view, setup_buttons_rpi, _confirm_by_user, update_gps_icon)
from threads import th_time, th_gps, th_ble, th_plt, th_ftp, th_net, th_cnv
from settings.utils_settings import yaml_load_pairs, json_gen_ddh
from threads.th import DDHThread
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from db.db_his import DBHis
from threads.utils import (
    update_dl_folder_list,
    json_get_ship_name,
    json_get_metrics,
    json_get_macs,
    json_mac_dns,
    json_get_forget_time_secs, json_get_span_dict, rpi_set_brightness, json_get_hci_if, setup_db_n_logs, json_get_pairs)
from logzero import logger as c_log
from threads.sig import (
    SignalsBLE,
    SignalsPLT,
    SignalsTime, SignalsGPS, SignalsFTP, SignalsNET, SignalsCNV)
import os
import gui.designer_main as d_m


class DDHQtApp(QMainWindow, d_m.Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        # checks
        if ctx.ftp_en:
            ftp_assert_credentials()

        # gui: view
        super(DDHQtApp, self).__init__(*args, **kwargs)
        self.plt_cnv = MplCanvas(self, width=5, height=3, dpi=100)
        setup_view(self, ctx.json_file)
        setup_buttons_gui(self)
        setup_db_n_logs()
        setup_his_tab(self)

        # uncommenting this can be useful when dev
        setup_window_center(self)
        setup_buttons_rpi(self, c_log)

        # gui: controller
        d = ctx.dl_files_folder
        self.sys_secs = 0
        self.bsy_dots = ''
        self.plt_timeout_dis = 0
        self.plt_timeout_msg = 0
        self.plt_folders = update_dl_folder_list(d)
        self.plt_folders_idx = 0
        self.plt_dir = None
        self.plt_time_spans = ('h', 'd', 'w', 'm', 'y')
        self.plt_ts_idx = 0
        self.plt_ts = self.plt_time_spans[0]
        self.plt_metrics = json_get_metrics(ctx.json_file)
        self.bright_idx = 2
        self.btn_3_held = 0
        self.tab_edit_hide = True
        self.tab_edit_wgt_ref = None
        self.key_shift = None
        self.last_time_icon_ble_press = 0
        hide_edit_tab(self)
        self._populate_history_tab()

        # threads
        self.th_time = None
        self.th_ble = None
        self.th_plt = None
        self.th_net = None
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(7)
        self._create_threads()
        self.thread_pool.start(self.th_time)
        self.thread_pool.start(self.th_gps)
        self.thread_pool.start(self.th_net)
        self.thread_pool.start(self.th_ftp)
        self.thread_pool.start(self.th_cnv)
        self.thread_pool.start(self.th_ble)

        # timer used to quit this app
        self.tim_q = QTimer()
        self.tim_q.timeout.connect(self._timer_bye)


    def _timer_bye(self):
        self.tim_q.stop()
        sys.exit(0)

    @pyqtSlot(str, name='slot_gui_update_time')
    def slot_gui_update_time(self, dots):
        # update GUI widgets
        self.sys_secs += 1
        self.bsy_dots = dots
        fmt = '%B %d,  %H:%M:%S'
        t = datetime.datetime.now().strftime(fmt)
        _ = self.lbl_time_n_pos.text().split('\n')
        s = '{}\n{}\n{}\n{}'.format(_[0], t, _[2], _[3])
        self.lbl_time_n_pos.setText(s)
        self.lbl_plt_bsy.setText(self.bsy_dots)

        # timeout to display plot tab, compare to 1 only runs once
        if self.plt_timeout_dis == 1:
            self.tabs.setCurrentIndex(0)
        if self.plt_timeout_dis > 0:
            self.plt_timeout_dis -= 1

        # timeout to display plot message
        if self.plt_timeout_msg == 1:
            self.lbl_plt_msg.clear()
            self.lbl_plt_msg.setVisible(False)
            self.slot_gui_update_plt('')
        if self.plt_timeout_msg > 0:
            self.plt_timeout_msg -= 1

        # things updated less often
        if self.sys_secs % 30 == 0:
            j = ctx.json_file
            s_n = json_get_ship_name(j)
            self.lbl_boatname.setText(s_n)

    @pyqtSlot(str, str, name='slot_gui_update_gps_pos')
    def slot_gui_update_gps_pos(self, lat, lon):
        _ = self.lbl_time_n_pos.text().split('\n')
        s = '{}\n{}\n{}\n{}'.format(_[0], _[1], lat, lon)
        self.lbl_time_n_pos.setText(s)
        ok = lat not in ['missing', 'searching']
        update_gps_icon(self, ok, lat, lon)

    @pyqtSlot(str, name='slot_gui_update_gps_time_via')
    def slot_gui_update_gps_time_via(self, via):
        _ = self.lbl_time_n_pos.text().split('\n')
        s = '{}\n{}\n{}\n{}'.format(via, _[1], _[2], _[3])
        self.lbl_time_n_pos.setText(s)

    @pyqtSlot(str, name='slot_gui_update_net')
    def slot_gui_update_net_via(self, via):
        via = via.replace('\n', '')
        _ = self.lbl_net_n_ftp.text().split('\n')
        s = '{}\n{}'.format(via, _[1])
        self.lbl_net_n_ftp.setText(s)

    @pyqtSlot(str, name='slot_gui_update_ftp')
    def slot_gui_update_ftp(self, c):
        _ = self.lbl_net_n_ftp.text().split('\n')
        s = '{}\n{}'.format(_[0], c)
        self.lbl_net_n_ftp.setText(s)

    @pyqtSlot(str, name='slot_gui_update_cnv')
    def slot_gui_update_cnv(self, s):
        _ = self.lbl_plot.text().split('\n')
        s = '{}\n{}'.format(_[0], s)
        self.lbl_plot.setText(s)

    @pyqtSlot(str, name='slot_gui_update_plt')
    def slot_gui_update_plt(self, s):
        _ = self.lbl_plot.text().split('\n')
        s = '{}\n{}'.format(s, _[1])
        self.lbl_plot.setText(s)

    @pyqtSlot(name='slot_plt_start')
    def slot_plt_start(self):
        ctx.plt_ongoing = True
        self.slot_gui_update_plt('Plotting...')
        self.lbl_plt_bsy.setVisible(True)

    @pyqtSlot(object, str, name='slot_plt_result')
    def slot_plt_result(self, result, s):
        if result:
            self.slot_gui_update_plt('plot ok')
            self.tabs.setCurrentIndex(1)
            to = ctx.PLT_SHOW_TIMEOUT
            self.plt_timeout_dis = to
        else:
            self.slot_gui_update_plt(s)
            self.slot_plt_msg(s)
        ctx.plt_ongoing = False
        self.lbl_plt_bsy.setVisible(False)

    @pyqtSlot(str, name='slot_plt_msg')
    def slot_plt_msg(self, desc):
        self.lbl_plt_msg.setText(desc)
        self.lbl_plt_msg.setVisible(True)
        self.plt_timeout_msg = ctx.PLT_MSG_TIMEOUT

    @pyqtSlot(str, name='slot_status')
    def slot_status(self, t):
        c_log.info(t)

    @pyqtSlot(str, name='slot_debug')
    def slot_debug(self, d):
        c_log.debug(d)

    @pyqtSlot(str, name='slot_warning')
    def slot_warning(self, e):
        c_log.warning(e)

    @pyqtSlot(str, name='slot_error')
    def slot_error(self, e):
        c_log.error(e)

    @pyqtSlot(str, name='slot_ble_scan_pre')
    def slot_ble_scan_pre(self, s):
        if ctx.ble_en:
            i = 'gui/res/img_blue_color.png'
        else:
            i = 'gui/res/img_blue.png'
        self.img_ble.setPixmap(QPixmap(i))
        self.bar_dl.setValue(0)
        self.lbl_ble.setText(s)

    @pyqtSlot(int, name='slot_ble_scan_post')
    def slot_ble_scan_post(self, n):
        if n:
            i = 'gui/res/img_blue_left.png'
            self.img_ble.setPixmap(QPixmap(i))

    # a download session consists of 1 to n loggers
    @pyqtSlot(str, int, int, name='slot_ble_session_pre')
    def slot_ble_session_pre(self, mac, val_1, val_2):
        # desc: mac, val_1: logger index, val_2: total num of loggers
        j = ctx.json_file
        s = 'logger {} of {}\n{}'
        s = s.format(val_1, val_2, json_mac_dns(j, mac))
        ctx.lg_num = s
        s = 'doing {}'.format(s)
        self.lbl_ble.setText(s)

    # indicates current logger of current download session
    @pyqtSlot(name='slot_ble_logger_pre')
    def slot_ble_logger_pre(self):
        t = 'configuring {}'.format(ctx.lg_num)
        self.lbl_ble.setText(t)
        ctx.lg_dl_size = 0
        ctx.lg_dl_bar_pc = 0
        self.bar_dl.setValue(0)

    @pyqtSlot(str, int, int, int, int, name='slot_ble_file_pre')
    def slot_ble_file_pre(self, _, dl_s, val_1, val_2, val_3):
        s = 'get file {} of {}\n{} minutes left'
        s = s.format(val_1, val_2, val_3)
        self.lbl_ble.setText(s)
        ctx.lg_dl_size = dl_s

    @pyqtSlot(int, name='slot_ble_file_post')
    def slot_ble_file_post(self, speed):
        s = 'BLE: approximate speed {} B/s'.format(speed)
        self.slot_status(s)

    @pyqtSlot(bool, str, str, name='slot_ble_logger_post')
    def slot_ble_logger_post(self, ok, s, mac):
        x = 100 if ok else 0
        self.bar_dl.setValue(x)
        self.lbl_ble.setText(s)
        if not ok:
            self.slot_his_update(mac, s, '')

    @pyqtSlot(str, name='slot_ble_logger_plot_req')
    def slot_ble_logger_plot_req(self, mac):
        if not mac:
            s = 'no plot from last logger'
            self.lbl_plot.setText(s)
            return
        d = ctx.dl_files_folder
        self.plt_folders = update_dl_folder_list(d)
        d = pathlib.Path(ctx.dl_files_folder)
        d = d / str(mac).replace(':', '-')
        self.plt_dir = str(d)
        self._throw_th_plt()

    @pyqtSlot(str, name='slot_ble_session_post')
    def slot_ble_session_post(self, desc):
        self.lbl_ble.setText(desc)

    @pyqtSlot(name='slot_ble_dl_step')
    def slot_ble_dl_step(self):
        # 128 is hardcoded XMODEM packet size
        pc = 100 * (128 / ctx.lg_dl_size)
        ctx.lg_dl_bar_pc += pc
        self.bar_dl.setValue(ctx.lg_dl_bar_pc)

    @pyqtSlot(str, str, str, name='slot_his_update')
    def slot_his_update(self, mac, lat, lon):
        j = ctx.json_file
        name = json_mac_dns(j, mac)
        frm = '%m/%d/%y %H:%M:%S'
        frm_t = datetime.datetime.now().strftime(frm)
        db = DBHis(ctx.db_his)
        if lat is None or lat == '':
            lat, lon = 'N/A', 'N/A'
        db.safe_update(mac, name, lat, lon, frm_t)
        self._populate_history_tab()

    def _click_btn_known_clear(self):
        self.lst_mac_org.clear()
        self.lst_mac_dst.clear()

    def _click_btn_see_all(self):
        # loads (mac, name) pairs from yaml file
        self.lst_mac_org.clear()
        r = str(ctx.app_conf_folder)
        f = QFileDialog.getOpenFileName(QFileDialog(),
                                        'Choose file', r,
                                        'YAML files (*.yml)')
        pairs = yaml_load_pairs(f)
        if not pairs:
            return
        for m, n in pairs.items():
            s = '{}  {}'.format(m, n)
            self.lst_mac_org.addItem(s)

    def _click_btn_see_cur(self):
        # loads (mac, name) pairs in ddh.json file
        self.lst_mac_org.clear()
        j = str(ctx.json_file)
        pairs = json_get_pairs(j)
        for m, n in pairs.items():
            s = '{}  {}'.format(m, n)
            self.lst_mac_org.addItem(s)

    def _click_btn_arrow(self):
        # dict from selected items in upper box
        ls = self.lst_mac_org.selectedItems()
        o = dict()
        for i in ls:
            pair = i.text().split()
            o[pair[0]] = pair[1]

        # dict from all items in lower box
        b = self.lst_mac_dst
        d_b = dict_from_list_view(b)
        d_b.update(o)

        # update lower box
        self.lst_mac_dst.clear()
        for m, n in d_b.items():
            s = '{}  {}'.format(m, n)
            self.lst_mac_dst.addItem(s)

    def _click_btn_setup_apply(self):
        # input: pairs we want to monitor
        l_v = self.lst_mac_dst
        pairs = dict_from_list_view(l_v)

        # input: forget_time value
        try:
            t = int(self.lne_forget.text())
        except ValueError:
            t = 0
        self.lne_forget.setText(str(t))

        # input: vessel name
        ves = self.lne_vessel.text()

        # check inputs prior writing ddh.conf file
        if t >= 3600 and ves and pairs:
            s = 'restarting DDH...'
            self.lbl_setup_result.setText(s)
            j = json_gen_ddh(pairs, ves, t)
            with open(ctx.json_file, 'w') as f:
                f.write(j)
            # bye, bye
            self.tim_q.start(2000)
            return

        # nope, not applying conf in form
        s = 'bad'
        self.lbl_setup_result.setText(s)

    def _click_icon_boat(self, _):
        c_log.debug('GUI: clicked secret bye!')
        self.closeEvent(_)

    def _click_icon_plot(self, _):
        # requires shift key
        if not self.key_shift:
            return
        self.showMinimized()

    def _release_icon_ble(self, _):
        t = self.last_time_icon_ble_press
        now = time.perf_counter()
        if now - t < 5:
            return

        ctx.ble_en = not ctx.ble_en
        b = int(ctx.ble_en)
        if b:
            p = 'gui/res/img_blue_color.png'
        else:
            p = 'gui/res/img_blue.png'
        self.img_ble.setPixmap(QPixmap(p))
        s = 'GUI: secret BLE hold {}'.format(b)
        c_log.debug(s)

    def _click_icon_ble(self, _):
        # statistics
        t = time.perf_counter()
        self.last_time_icon_ble_press = t

        # allow to click or not
        if not ctx.sw_ble_en:
            return

        # requires shift key
        if not self.key_shift:
            return

        ctx.ble_en = not ctx.ble_en
        b = int(ctx.ble_en)
        if b:
            p = 'gui/res/img_blue_color.png'
        else:
            p = 'gui/res/img_blue.png'
        self.img_ble.setPixmap(QPixmap(p))
        s = 'GUI: secret BLE tap {}'.format(b)
        c_log.debug(s)

    def _click_icon_gps(self, _):
        s = 'GUI: secret GPS tap {}'.format(self.bright_idx)
        c_log.debug(s)

        if linux_is_rpi():
            self.bright_idx = (self.bright_idx + 1) % 3
            v = self.bright_idx
            rpi_set_brightness(v)

    def _click_icon_net(self, _):
        # self.tab_edit_hide = not self.tab_edit_hide
        s = 'GUI: secret NET click'
        c_log.debug(s)

        # requires shift key
        if not self.key_shift:
            return
        self.tab_edit_hide = not self.tab_edit_hide

        if self.tab_edit_hide:
            hide_edit_tab(self)
        else:
            icon = QIcon('gui/res/icon_setup.png')
            self.tabs.addTab(self.tab_edit_wgt_ref, icon, ' Setup')
            self.tabs.setCurrentIndex(3)

    def _click_btn_dl_purge(self):
        s = 'sure to empty dl_files folder?'
        if _confirm_by_user(s):
            d = pathlib.Path(ctx.dl_files_folder)
            try:
                # safety check
                if 'dl_files' not in str(d):
                    return
                shutil.rmtree(str(d), ignore_errors=True)
                self.plt_folders = update_dl_folder_list(d)
                self.plt_folders_idx = 0
                self.plt_dir = None
            except OSError as e:
                print('error {} : {}'.format(d, e))

    def _click_btn_his_purge(self):
        s = 'sure to purge history?'
        if _confirm_by_user(s):
            db = DBHis(ctx.db_his)
            db.delete_all_records()
            db = DBHis(ctx.db_blk)
            db.delete_all_records()
        self._populate_history_tab()

    def _click_btn_load_current(self):
        j = ctx.json_file
        ves = json_get_ship_name(j)
        f_t = json_get_forget_time_secs(j)
        self.lne_vessel.setText(ves)
        self.lne_forget.setText(str(f_t))

    def _create_threads(self):
        # time
        self.th_time = DDHThread(th_time.fxn, SignalsTime)
        self.th_time.signals().time_update.connect(self.slot_gui_update_time)
        self.th_time.signals().time_status.connect(self.slot_status)

        # gps
        self.th_gps = DDHThread(th_gps.fxn, SignalsGPS)
        self.th_gps.signals().gps_status.connect(self.slot_status)
        self.th_gps.signals().gps_update_time_via.connect(self.slot_gui_update_gps_time_via)
        self.th_gps.signals().gps_update_pos.connect(self.slot_gui_update_gps_pos)
        self.th_gps.signals().gps_error.connect(self.slot_error)

        # ble
        k = json_get_macs(ctx.json_file)
        ft_s = json_get_forget_time_secs(ctx.json_file)
        h = json_get_hci_if(ctx.json_file)
        arg = [ft_s, 60, k, h]
        self.th_ble = DDHThread(th_ble.fxn, SignalsBLE, arg)
        self.th_ble.signals().ble_status.connect(self.slot_status)
        self.th_ble.signals().ble_debug.connect(self.slot_debug)
        self.th_ble.signals().ble_error.connect(self.slot_error)
        self.th_ble.signals().ble_scan_pre.connect(self.slot_ble_scan_pre)
        self.th_ble.signals().ble_scan_post.connect(self.slot_ble_scan_post)
        self.th_ble.signals().ble_session_pre.connect(self.slot_ble_session_pre)
        self.th_ble.signals().ble_logger_pre.connect(self.slot_ble_logger_pre)
        self.th_ble.signals().ble_file_pre.connect(self.slot_ble_file_pre)
        self.th_ble.signals().ble_file_post.connect(self.slot_ble_file_post)
        self.th_ble.signals().ble_logger_post.connect(self.slot_ble_logger_post)
        self.th_ble.signals().ble_session_post.connect(self.slot_ble_session_post)
        self.th_ble.signals().ble_deployed.connect(self.slot_his_update)
        self.th_ble.signals().ble_dl_step.connect(self.slot_ble_dl_step)
        self.th_ble.signals().ble_logger_plot_req.connect(self.slot_ble_logger_plot_req)

        # ftp
        self.th_ftp = DDHThread(th_ftp.fxn, SignalsFTP)
        self.th_ftp.signals().ftp_update.connect(self.slot_gui_update_ftp)
        self.th_ftp.signals().ftp_error.connect(self.slot_error)
        self.th_ftp.signals().ftp_status.connect(self.slot_status)

        # network
        self.th_net = DDHThread(th_net.fxn, SignalsNET)
        self.th_net.signals().net_status.connect(self.slot_status)
        self.th_net.signals().net_update.connect(self.slot_gui_update_net_via)

        # conversion
        self.th_cnv = DDHThread(th_cnv.fxn, SignalsCNV)
        self.th_cnv.signals().cnv_update.connect(self.slot_gui_update_cnv)
        self.th_cnv.signals().cnv_status.connect(self.slot_status)
        self.th_cnv.signals().cnv_error.connect(self.slot_error)

    def _throw_th_plt(self):
        ax = self.plt_cnv.axes
        arg = [self.plt_dir, ax, self.plt_ts, self.plt_metrics]
        self.th_plt = DDHThread(th_plt.fxn, SignalsPLT, arg)
        self.th_plt.signals().plt_status.connect(self.slot_status)
        self.th_plt.signals().plt_error.connect(self.slot_error)
        self.th_plt.signals().plt_result.connect(self.slot_plt_result)
        self.th_plt.signals().plt_start.connect(self.slot_plt_start)
        self.th_plt.signals().plt_msg.connect(self.slot_plt_msg)
        self.thread_pool.start(self.th_plt)

    def closeEvent(self, event):
        event.accept()
        c_log.debug('SYS: closing GUI ...')
        sys.stderr.close()
        sys.exit(0)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Shift:
            self.key_shift = 0

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Shift:
            self.key_shift = 1

        known = [Qt.Key_1, Qt.Key_3, Qt.Key_Shift]
        if e.key() not in known:
            # this may fire with alt + tab too
            e = 'GUI: unknown keypress'
            c_log.debug(e)
            return

        # prevent div by zero
        if not self.plt_folders:
            c_log.debug('GUI: no data folders')
            e = 'no plot folders'
            self.slot_gui_update_plt(e)
            return

        # emulate raspberry button presses, no holds
        if e.key() == Qt.Key_1:
            c_log.debug('GUI: keypress 1')
            self.plt_folders_idx += 1
            self.plt_folders_idx %= len(self.plt_folders)
            self.plt_dir = self.plt_folders[self.plt_folders_idx]
        elif e.key() == Qt.Key_2:
            c_log.debug('GUI: keypress 2')
        elif e.key() == Qt.Key_3:
            self.plt_ts_idx += 1
            self.plt_ts_idx %= len(self.plt_time_spans)
            self.plt_ts = self.plt_time_spans[self.plt_ts_idx]
            c_log.debug('GUI: keypress 3')
        # emulate raspberry button holds
        elif e.key() == Qt.Key_4:
            c_log.debug('GUI: keypress 4')
        elif e.key() == Qt.Key_5:
            c_log.debug('GUI: keypress 5')
        elif e.key() == Qt.Key_6:
            c_log.debug('GUI: keypress 6')
        elif e.key() == Qt.Key_Shift:
            c_log.debug('GUI: keypress left shift')
            return
        else:
            c_log.debug('GUI: keypress unknown')
            return

        # prevent span before first plot
        if not self.plt_dir:
            c_log.error('GUI: no plot to set span')
            return

        # plot unless busy doing a previous one
        if not ctx.plt_ongoing:
            self._throw_th_plt()
        else:
            c_log.debug('GUI: busy to plot')

    def _populate_history_tab(self):
        utils_gui.setup_his_tab(self)


def on_ctrl_c(signal_num, _):
    c_log.debug('SYS: captured signal {}'.format(signal_num))
    os._exit(signal_num)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
