import queue
import threading
from mat.agent_gps import AgentGPS
from mat.linux import linux_is_rpi
from threads.th_gps import get_gps_data
from threads.utils_ftp import ftp_assert_credentials
from threads.utils_macs import black_macs_delete_all
import datetime
import pathlib
import shutil
import sys
from settings import ctx
from PyQt5.QtCore import (
    Qt,
    pyqtSlot,
    QTimer)
from PyQt5.QtGui import (
    QPixmap,
    QIcon)
from PyQt5.QtWidgets import (
    QMainWindow,
    QFileDialog)
from gui import utils_gui
from gui.utils_gui import (
    setup_view, setup_his_tab, setup_buttons_gui, setup_window_center, hide_edit_tab,
    dict_from_list_view, setup_buttons_rpi, _confirm_by_user, update_gps_icon)
from threads import th_time, th_gps, th_ble, th_plt, th_ftp, th_net, th_cnv
from settings.utils_settings import yaml_load_pairs, json_gen_ddh
from threads.th import DDHThread
from db.db_his import DBHis
from threads.utils import (
    update_dl_folder_list,
    json_get_ship_name,
    json_get_metrics,
    json_get_macs,
    json_mac_dns,
    json_get_forget_time_secs, rpi_set_brightness, json_get_hci_if, rm_plot_db, json_get_pairs, setup_app_log,
    update_cnv_log_err_file)
from logzero import logger as c_log
from threads.sig import (
    SignalsBLE,
    SignalsPLT,
    SignalsTime, SignalsGPS, SignalsFTP, SignalsNET, SignalsCNV)
import os
import gui.designer_main as d_m
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class DDHQtApp(QMainWindow, d_m.Ui_MainWindow):

    def __init__(self):
        # checks
        _ftp_credentials_check()

        # gui: view
        super(DDHQtApp, self).__init__()
        self.plt_cnv = MplCanvas(self, width=5, height=3, dpi=100)
        setup_view(self, ctx.json_file)
        setup_buttons_gui(self)
        setup_his_tab(self)
        setup_app_log(str(ctx.app_logs_folder / 'ddh.log'))
        setup_window_center(self)
        setup_buttons_rpi(self, c_log)

        # gui: controller
        self.gps_last_ts = None
        self.sys_secs = 0
        self.bsy_dots = ''
        self.plt_timeout_dis = 0
        self.plt_timeout_msg = 0
        self.plt_folders = update_dl_folder_list(ctx.dl_files_folder)
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
        rm_plot_db()

        #
        # # ftp
        # self.th_ftp = DDHThread(th_ftp.fxn, SignalsFTP)
        # self.th_ftp.signals().ftp_update.connect(self.slot_gui_update_ftp)
        # self.th_ftp.signals().ftp_error.connect(self.slot_error)
        # self.th_ftp.signals().ftp_status.connect(self.slot_status)
        #

        # signals and slots
        self.sig_gps = SignalsGPS()
        self.sig_cnv = SignalsCNV()
        self.sig_tim = SignalsTime()
        self.sig_net = SignalsNET()
        self.sig_plt = SignalsPLT()
        self.sig_ble = SignalsBLE()
        self.sig_ble.status.connect(self.slot_status)
        self.sig_gps.status.connect(self.slot_status)
        self.sig_cnv.status.connect(self.slot_status)
        self.sig_net.status.connect(self.slot_status)
        self.sig_plt.status.connect(self.slot_status)
        self.sig_gps.error.connect(self.slot_error)
        self.sig_cnv.error.connect(self.slot_error)
        self.sig_plt.error.connect(self.slot_error)
        self.sig_ble.error.connect(self.slot_error)
        self.sig_cnv.update.connect(self.slot_gui_update_cnv)
        self.sig_gps.update.connect(self.slot_gui_update_gps)
        self.sig_tim.update.connect(self.slot_gui_update_time)
        self.sig_net.update.connect(self.slot_gui_update_net)
        self.sig_plt.update.connect(self.slot_gui_update_plt)
        self.sig_plt.start.connect(self.slot_plt_start)
        self.sig_plt.msg.connect(self.slot_plt_msg)
        self.sig_plt.end.connect(self.slot_plt_end)
        self.sig_ble.debug.connect(self.slot_debug)
        self.sig_ble.scan_pre.connect(self.slot_ble_scan_pre)
        self.sig_ble.scan_post.connect(self.slot_ble_scan_post)
        self.sig_ble.session_pre.connect(self.slot_ble_session_pre)
        self.sig_ble.logger_pre.connect(self.slot_ble_logger_pre)
        self.sig_ble.file_pre.connect(self.slot_ble_file_pre)
        self.sig_ble.file_post.connect(self.slot_ble_file_post)
        self.sig_ble.logger_post.connect(self.slot_ble_logger_post)
        self.sig_ble.session_post.connect(self.slot_ble_session_post)
        self.sig_ble.deployed.connect(self.slot_his_update)
        self.sig_ble.dl_step.connect(self.slot_ble_dl_step)
        self.sig_ble.dl_warning.connect(self.slot_ble_dl_warning)
        self.sig_ble.logger_plot_req.connect(self.slot_ble_logger_plot_req)

        # queues for app to query agents
        self.qgi, self.qgo = queue.Queue(), queue.Queue()
        self.qpi, self.qpo = queue.Queue(), queue.Queue()

        # agent threads
        self.ag_gps = None
        self.ag_gps = AgentGPS(self.qgi, self.qgo)
        self.ag_gps.start()

        # self.thread_pool.start(self.th_ftp)
        # self.thread_pool.start(self.th_ble)

        # first thing this app does is try to time sync
        get_gps_data(self)

        # app threads
        self.th_gps = threading.Thread(target=th_gps.loop, args=(self, ))
        self.th_time = threading.Thread(target=th_time.loop, args=(self, ))
        self.th_cnv = threading.Thread(target=th_cnv.loop, args=(self, ))
        self.th_net = threading.Thread(target=th_net.loop, args=(self, ))
        self.th_plt = threading.Thread(target=th_plt.loop, args=(self, ))
        self.th_ble = threading.Thread(target=th_ble.loop, args=(self, ))
        self.th_gps.start()
        self.th_time.start()
        self.th_cnv.start()
        self.th_net.start()
        self.th_plt.start()
        self.th_ble.start()


        # timer used to quit this app
        self.tim_q = QTimer()
        self.tim_q.timeout.connect(self._timer_bye)

    def _timer_bye(self):
        self.tim_q.stop()
        os._exit(0)

    @pyqtSlot(str, name='slot_gui_update_time')
    def slot_gui_update_time(self, dots):
        self.sys_secs += 1
        self.bsy_dots = dots
        fmt = '%b %d %H:%M:%S'
        t = datetime.datetime.now().strftime(fmt)
        _ = self.lbl_time_n_pos.text().split('\n')
        s = '{}\n{}\n{}\n{}'.format(_[0], _[1], _[2], t)
        self.lbl_time_n_pos.setText(s)
        self.lbl_plt_bsy.setText(self.bsy_dots)
        print(t)

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

    @pyqtSlot(tuple, name='slot_gui_update_gps')
    def slot_gui_update_gps(self, u):
        """ updates GUI GPS lat, lon, timestamp """
        lat, lon, self.gps_last_ts = u
        _ = self.lbl_time_n_pos.text().split('\n')
        s = '{}\n{}\n{}\n{}'.format('GPS', lat, lon, _[3])
        self.lbl_time_n_pos.setText(s)
        ok = lon not in ['missing', 'searching', 'malfunction']
        update_gps_icon(self, ok, lat, lon)

    @pyqtSlot(str, name='slot_gui_update_net')
    def slot_gui_update_net(self, via):
        # SSID_or_CELL / FTP
        via = via.replace('\n', '')
        _ = self.lbl_net_n_ftp.text().split('\n')
        s = '{}\n{}'.format(via, _[1])
        self.lbl_net_n_ftp.setText(s)

    @pyqtSlot(str, name='slot_gui_update_ftp')
    def slot_gui_update_ftp(self, c):
        _ = self.lbl_net_n_ftp.text().split('\n')
        s = '{}\n{}'.format(_[0], c)
        self.lbl_net_n_ftp.setText(s)

    @pyqtSlot(list, name='slot_gui_update_cnv')
    def slot_gui_update_cnv(self, _e):
        path = str(ctx.app_logs_folder / 'ddh_err_cnv.log')
        update_cnv_log_err_file(path, _e)
        s = 'some bad conversion' if _e else 'conversion OK'
        _ = self.lbl_plot.text().split('\n')
        s = '{}\n{}\n{}'.format(_[0], s, _[2])
        self.lbl_plot.setText(s)

    @pyqtSlot(str, name='slot_gui_update_plt')
    def slot_gui_update_plt(self, s):
        _ = self.lbl_plot.text().split('\n')
        s = '{}\n{}\n{}'.format(s, _[1], _[2])
        self.lbl_plot.setText(s)

    @pyqtSlot(list, name='slot_ble_dl_warning')
    def slot_ble_dl_warning(self, w):
        lbl = self.lbl_plot
        _ = lbl.text().split('\n')
        style = 'color: {}; font: 18pt'
        if not w:
            s = '{}\n{}\n{}'.format(_[0], _[1], '')
            lbl.setStyleSheet(style.format('black'))
            lbl.setText(s)
            return
        _arp = json_mac_dns(ctx.json_file, w[0])
        _e = '{} not deployed'.format(_arp)
        s = '{}\n{}\n{}'.format(_[0], _[1], _e)
        lbl.setStyleSheet(style.format('orange'))
        lbl.setText(s)

    @pyqtSlot(name='slot_plt_start')
    def slot_plt_start(self):
        self.slot_gui_update_plt('Plotting...')
        self.lbl_plt_bsy.setVisible(True)

    @pyqtSlot(object, str, name='slot_plt_end')
    def slot_plt_end(self, result, s):
        if result:
            self.slot_gui_update_plt('plot ok')
            self.tabs.setCurrentIndex(1)
            to = ctx.PLT_SHOW_TIMEOUT
            self.plt_timeout_dis = to
        else:
            self.slot_gui_update_plt(s)
            self.slot_plt_msg(s)
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
        self.bar_dl.setValue(0)
        self.lbl_ble.setText(s)
        r = ctx.app_res_folder
        p = '{}/img_blue_color.png'.format(r)
        if not ctx.ble_en:
            p = '{}/img_blue.png'.format(r)
        self.img_ble.setPixmap(QPixmap(p))

    @pyqtSlot(int, name='slot_ble_scan_post')
    def slot_ble_scan_post(self, n):
        pass

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
            self.slot_gui_update_plt(s)
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

    def _click_icon_ble(self, _):
        # allow to click or not
        if not ctx.sw_ble_en:
            return

        # requires shift key
        if not self.key_shift:
            return

        ctx.ble_en = not ctx.ble_en
        r = ctx.app_res_folder
        b = int(ctx.ble_en)
        p = '{}/img_blue_color.png'.format(r)
        if not b:
            p = '{}/img_blue.png'.format(r)
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
            black_macs_delete_all(ctx.db_blk)
        self._populate_history_tab()

    def _click_btn_load_current(self):
        j = ctx.json_file
        ves = json_get_ship_name(j)
        f_t = json_get_forget_time_secs(j)
        self.lne_vessel.setText(ves)
        self.lne_forget.setText(str(f_t))

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
        os._exit(0)

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
        ctx.sem_plt.acquire()
        self._throw_th_plt()
        ctx.sem_plt.release()

    def _populate_history_tab(self):
        utils_gui.setup_his_tab(self)


def on_ctrl_c(signal_num, _):
    c_log.debug('SYS: captured signal {}'.format(signal_num))
    os._exit(signal_num)


def _ftp_credentials_check():
    if ctx.ftp_en:
        ftp_assert_credentials()


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
