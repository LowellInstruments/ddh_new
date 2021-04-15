import datetime
import os
import pathlib
import queue
import shutil
import sys
import threading

import matplotlib
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
from logzero import logger as c_log

import ddh.gui.designer_main as d_m
from ddh.db.db_his import DBHis
from ddh.gui.utils_gui import (
    setup_view, setup_his_tab, setup_buttons_gui, setup_window_center, hide_edit_tab,
    dict_from_list_view, setup_buttons_rpi, _confirm_by_user, paint_gps_icon_w_color_land_sea, populate_history_tab,
    paint_gps_icon_w_color_dis_or_cache, hide_error_tab, show_error_tab, show_edit_tab, connect_gui_signals_n_slots)
from ddh.settings import ctx
from ddh.settings.utils_settings import yaml_load_pairs, gen_ddh_json_content
from ddh.threads import th_ble, th_cnv, th_plt, th_gps, th_aws, th_net, th_boot, th_time
from ddh.threads.sig import (
    SignalsBLE,
    SignalsPLT,
    SignalsTime, SignalsGPS, SignalsNET, SignalsCNV, SignalsAWS, SignalsBoot)
from ddh.threads.utils import (
    update_dl_folder_list,
    json_get_ship_name,
    json_get_metrics,
    json_mac_dns,
    json_get_forget_time_secs, rpi_set_brightness, rm_plot_db, json_get_pairs, setup_app_log,
    update_cnv_log_err_file, json_set_plot_units, json_get_gps_enforced)
from ddh.threads.utils_aws import aws_credentials_assert
from ddh.threads.utils_gps_quectel import utils_gps_backup_set
from ddh.threads.utils_macs import delete_color_mac_file
from mat.utils import linux_is_rpi

matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class DDHQtApp(QMainWindow, d_m.Ui_MainWindow):

    def __init__(self):
        _aws_credentials_check()
        _sudo_permissions_check()

        # gui: view
        super(DDHQtApp, self).__init__()
        self.plt_cnv = MplCanvas(self, width=5, height=3, dpi=100)
        setup_view(self, ctx.app_json_file)
        setup_buttons_gui(self)
        setup_his_tab(self)
        setup_app_log(str(ctx.app_logs_folder / 'ddh.log'))
        setup_window_center(self)
        setup_buttons_rpi(self, c_log)
        rpi_set_brightness(100)

        # gui: controller
        self.gps_last_ts = None
        self.sys_secs = 0
        self.bsy_dots = ''
        self.plt_timeout_dis = 0
        self.plt_timeout_msg = 0
        self.plt_folders = update_dl_folder_list(ctx.app_dl_folder)
        self.plt_folders_idx = 0
        self.plt_dir = None
        self.plt_time_spans = ('h', 'd', 'w', 'm', 'y')
        self.plt_ts_idx = 0
        self.plt_ts = self.plt_time_spans[0]
        self.plt_metrics = json_get_metrics(ctx.app_json_file)
        self.bright_idx = 2
        self.btn_3_held = 0
        self.tab_edit_hide = True
        self.tab_edit_wgt_ref = None
        self.tab_err_wgt_ref = None
        self.key_shift = None
        self.last_time_icon_ble_press = 0
        self.gps_enforced = json_get_gps_enforced(ctx.app_json_file)
        json_set_plot_units(ctx.app_json_file)
        hide_edit_tab(self)
        hide_error_tab(self)
        populate_history_tab(self)
        rm_plot_db()

        # signals and slots
        self.sig_gps = SignalsGPS()
        self.sig_cnv = SignalsCNV()
        self.sig_tim = SignalsTime()
        self.sig_net = SignalsNET()
        self.sig_plt = SignalsPLT()
        self.sig_ble = SignalsBLE()
        self.sig_aws = SignalsAWS()
        self.sig_boot = SignalsBoot()
        connect_gui_signals_n_slots(self)

        # app: prepare boot thread
        evb = threading.Event()
        self.qpi, self.qpo = queue.Queue(), queue.Queue()
        self.th_boot = threading.Thread(target=th_boot.boot, args=(self, evb))

        # app: prepare rest of threads, which boot slightly later
        self.th_time = threading.Thread(target=th_time.loop, args=(self, evb))
        self.th_gps = threading.Thread(target=th_gps.loop, args=(self, evb))
        self.th_cnv = threading.Thread(target=th_cnv.loop, args=(self, evb))
        self.th_net = threading.Thread(target=th_net.loop, args=(self, evb))
        self.th_plt = threading.Thread(target=th_plt.loop, args=(self, evb))
        self.th_ble = threading.Thread(target=th_ble.loop, args=(self, evb))
        self.th_aws = threading.Thread(target=th_aws.loop, args=(self, evb))
        self.th_boot.start()
        self.th_gps.start()
        self.th_time.start()
        self.th_cnv.start()
        self.th_net.start()
        self.th_plt.start()
        self.th_ble.start()
        self.th_aws.start()

        # timer used to quit this app
        self.tim_q = QTimer()
        self.tim_q.timeout.connect(self._timer_bye)

        # timer used to simulate errors
        # hide_error_tab(self)
        # self.tim_e = QTimer()
        # self.tim_e.timeout.connect(self._timer_err)
        # self.tim_e.start(5000)

    def _timer_bye(self):
        self.tim_q.stop()
        os._exit(0)

    # def _timer_err(self):
    #     self.slot_ble_logger_gps_nope('sim_mac')
    #     self.tim_e.stop()

    @pyqtSlot(str, name='slot_gui_update_time')
    def slot_gui_update_time(self, dots):
        """ th_time sends the signal for this slot """

        self.sys_secs += 1
        self.bsy_dots = dots
        fmt = '%b %d %H:%M:%S'
        t = datetime.datetime.now().strftime(fmt)
        _ = self.lbl_time_n_pos.text().split('\n')
        s = '{}\n{}\n{}\n{}'.format(_[0], _[1], _[2], t)
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
            j = ctx.app_json_file
            s_n = json_get_ship_name(j)
            self.lbl_boatname.setText(s_n)

    @pyqtSlot(str, name='slot_gui_update_time_source')
    def slot_gui_update_time_source(self, s):
        """ th_time sends the signal for this slot """

        _ = self.lbl_time_n_pos.text().split('\n')
        s = '{}\n{}\n{}\n{}'.format(s, _[1], _[2], _[3])
        self.lbl_time_n_pos.setText(s)

    @pyqtSlot(object, name='slot_gui_update_gps_pos')
    def slot_gui_update_gps_pos(self, u):
        """ th_gps sends the signal for this slot """

        # save current content (cc) of GUI
        cc = self.lbl_time_n_pos.text().split('\n')

        # u: lat, lon, timestamp
        lat, lon, self.gps_last_ts = ('N/A',) * 3
        if u:
            lat = '{:+.6f}'.format(float(u[0]))
            lon = '{:+.6f}'.format(float(u[1]))
            self.gps_last_ts = u[2]

        s = '{}\n{}\n{}\n{}'.format(cc[0], lat, lon, cc[3])
        self.lbl_time_n_pos.setText(s)
        if u:
            paint_gps_icon_w_color_land_sea(self, lat, lon)
        else:
            paint_gps_icon_w_color_dis_or_cache(self)

    @pyqtSlot(str, name='slot_gui_update_net_source')
    def slot_gui_update_net_source(self, s):
        """ th_net sends the signal for this slot """

        s = s.replace('\n', '')
        self.slot_status('NET: {}'.format(s))
        _ = self.lbl_net_n_cloud.text().split('\n')
        v = '{}\n{}'.format(s, _[1])
        self.lbl_net_n_cloud.setText(v)

    @pyqtSlot(str, name='slot_gui_update_aws')
    def slot_gui_update_aws(self, c):
        """ th_aws sends the signal for this slot """

        _ = self.lbl_net_n_cloud.text().split('\n')
        s = '{}\n{}'.format(_[0], c)
        self.lbl_net_n_cloud.setText(s)

    @pyqtSlot(list, name='slot_gui_update_cnv')
    def slot_gui_update_cnv(self, _e):
        """ th_cnv sends the signal for this slot """

        path = str(ctx.app_logs_folder / 'ddh_err_cnv.log')
        update_cnv_log_err_file(path, _e)
        s = 'CNV: error' if _e else 'conversion OK'
        _ = self.lbl_plot.text().split('\n')
        # lbl_plot.text: {PLT} {CNV} {ERR}
        s = '{}\n{}\n{}'.format(_[0], s, _[2])
        self.lbl_plot.setText(s)

    @pyqtSlot(str, name='slot_gui_update_plt')
    def slot_gui_update_plt(self, s):
        """ th_plt sends the signal for this slot """

        _ = self.lbl_plot.text().split('\n')
        # lbl_plot.text: {PLT} {CNV} {ERR}
        s = '{}\n{}\n{}'.format(s, _[1], _[2])
        self.lbl_plot.setText(s)

    @pyqtSlot(name='slot_plt_start')
    def slot_plt_start(self):
        """ th_plt sends the signal for this slot """

        self.slot_gui_update_plt('Plotting...')
        self.lbl_plt_bsy.setVisible(True)

    @pyqtSlot(object, str, name='slot_plt_end')
    def slot_plt_end(self, result, s):
        """ th_plt sends the signal for this slot """

        if result:
            self.slot_gui_update_plt('plot OK')
            self.tabs.setCurrentIndex(1)
            to = ctx.PLT_SHOW_TIMEOUT
            self.plt_timeout_dis = to
        else:
            self.slot_gui_update_plt(s)
            self.slot_plt_msg(s)
        self.lbl_plt_bsy.setVisible(False)

    @pyqtSlot(str, name='slot_plt_msg')
    def slot_plt_msg(self, desc):
        """ th_plt sends the signal for this slot """

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

    @pyqtSlot(str, name='slot_ble_logger_gps_nope')
    def slot_ble_logger_gps_nope(self, mac):

        # GPS not found, ends up updating history tab
        show_error_tab(self)
        self.slot_error('no GPS fix for {}'.format(mac))
        self.slot_his_update(mac, 'no GPS fix', '')

    @pyqtSlot(list, name='slot_ble_logger_to_orange')
    def slot_ble_logger_to_orange(self, w):
        """ th_ble sends the signal for this slot """

        # grab GUI current content
        lbl = self.lbl_plot
        _ = lbl.text().split('\n')
        style = 'color: {}; font: 18pt'

        # lbl_plot.text: {PLT} {CNV} {ERR}
        if not w:
            s = '{}\n{}\n{}'.format(_[0], _[1], '')
            lbl.setStyleSheet(style.format('black'))
            lbl.setText(s)
            return

        # some logger not re-deployed
        _arp = json_mac_dns(ctx.app_json_file, w[0])
        _e = '{} check history'.format(_arp)
        s = '{}\n{}\n{}'.format(_[0], _[1], _e)
        lbl.setStyleSheet(style.format('orange'))
        lbl.setText(s)

    @pyqtSlot(str, name='slot_ble_scan_pre')
    def slot_ble_scan_pre(self, s):
        """ th_ble sends the signal for this slot """

        self.bar_dl.setValue(0)
        self.lbl_ble.setText(s)
        r = ctx.app_res_folder
        p = '{}/img_blue_color.png'.format(r)
        if not ctx.ble_en:
            p = '{}/img_blue.png'.format(r)
        self.img_ble.setPixmap(QPixmap(p))

    @pyqtSlot(name='slot_ble_logger_dl_start')
    def slot_ble_logger_dl_start(self):
        """ th_ble sends the signal for this slot """

        t = 'querying {}'.format(ctx.lg_num)
        self.lbl_ble.setText(t)
        ctx.lg_dl_size = 0
        ctx.lg_dl_bar_pc = 0
        self.bar_dl.setValue(0)

    @pyqtSlot(str, int, int, int, int, name='slot_ble_logger_dl_start_file')
    def slot_ble_logger_dl_start_file(self, _, dl_s, val_1, val_2, val_3):
        """ th_ble sends the signal for this slot """

        s = 'file {} of {}\n{} minutes left'
        s = s.format(val_1, val_2, val_3)
        self.lbl_ble.setText(s)
        ctx.lg_dl_size = dl_s

    @pyqtSlot(bool, str, str, name='slot_ble_logger_end')
    def slot_ble_logger_end(self, ok, s, mac):
        """ th_ble sends the signal for this slot """

        self.bar_dl.setValue(100 if ok else 0)
        self.lbl_ble.setText(s)

        # on error, piggyback to history update slot / tab
        if not ok:
            e = s
            self.slot_his_update(mac, e, '')

    @pyqtSlot(str, name='slot_ble_logger_plot_req')
    def slot_ble_logger_plot_req(self, mac):
        """ th_ble sends the signal for this slot """

        if not mac:
            s = 'no plot from last logger'
            self.slot_gui_update_plt(s)
            return
        d = ctx.app_dl_folder
        self.plt_folders = update_dl_folder_list(d)
        d = pathlib.Path(ctx.app_dl_folder)
        d = d / str(mac).replace(':', '-')
        self.plt_dir = str(d)

        # collect args needed by th_plot
        ax = self.plt_cnv.axes
        ts = self.plt_ts
        met = self.plt_metrics
        d = self.plt_dir
        plt_args = (d, ax, ts, met)
        self.qpo.put(plt_args, timeout=1)

    @pyqtSlot(name='slot_ble_dl_progress_file')
    def slot_ble_dl_progress_file(self):
        """ th_ble sends the signal for this slot """

        # 128: hardcoded XMODEM packet size
        # step = 128

        # 2048: hardcoded when using DWG
        pc = 100 * (2048 / ctx.lg_dl_size)
        ctx.lg_dl_bar_pc += pc
        self.bar_dl.setValue(ctx.lg_dl_bar_pc)

    @pyqtSlot(str, str, str, name='slot_his_update')
    def slot_his_update(self, mac, lat, lon):
        """
        th_ble emits 'deployed' signal for this slot, at success
        also called by slot_ble_logger_after: at ble_interact error / AppBLEException
        also called by slot_ble_logger_gps_nope
        """

        # note: 'lat' parameter can piggyback an error message
        j = ctx.app_json_file
        name = json_mac_dns(j, mac)
        frm = '%Y/%m/%d %H:%M:%S'
        frm_t = datetime.datetime.now().strftime(frm)
        db = DBHis(ctx.db_his)
        if lat is None or lat == '':
            lat, lon = 'N/A', 'N/A'
        db.safe_update(mac, name, lat, lon, frm_t)

        # re-display updated history database
        populate_history_tab(self)

    def click_btn_clear_known_mac_list(self):
        self.lst_mac_org.clear()
        self.lst_mac_dst.clear()

    def click_btn_clear_see_all_macs(self):
        """ loads (mac, name) pairs from yaml file """

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

    def click_btn_see_macs_in_current_json_file(self):
        """ loads (mac, name) pairs in ddh.json file """

        self.lst_mac_org.clear()
        j = str(ctx.app_json_file)
        pairs = json_get_pairs(j)
        for m, n in pairs.items():
            s = '{}  {}'.format(m, n)
            self.lst_mac_org.addItem(s)

    def click_btn_arrow_move_entries(self):
        """ move items in upper box to lower box """

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

    def click_btn_apply_write_json_file(self):
        """ creates a user ddh.json file """

        l_v = self.lst_mac_dst
        pairs = dict_from_list_view(l_v)

        # input: <mac, name> pairs and forget_time
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
            j = gen_ddh_json_content(pairs, ves, t)
            with open(ctx.app_json_file, 'w') as f:
                f.write(j)
            # bye, bye
            self.tim_q.start(2000)
            return

        # nope, not applying conf in form
        s = 'bad'
        self.lbl_setup_result.setText(s)

    def click_icon_boat(self, _):
        """ clicking icon boat closes the DDH app """

        c_log.debug('GUI: clicked secret bye!')
        self.closeEvent(_)

    def click_icon_plot(self, ev):
        """ clicking shift + plot icon minimizes the app """

        ev.accept()
        s = 'GUI: secret PLT click, shift pressed = {}'
        c_log.debug(s.format(self.key_shift))

        if not self.key_shift:
            return
        self.key_shift = 0
        self.showMinimized()

    def click_icon_ble(self, ev):
        """ clicking shift + BLE icon disables bluetooth thread """

        ev.accept()
        s = 'GUI: secret BLE click, shift pressed = {}'
        c_log.debug(s.format(self.key_shift))

        # allows this feature or not
        if not ctx.sw_ble_en:
            return
        if not self.key_shift:
            return
        self.key_shift = 0

        ctx.ble_en = not ctx.ble_en
        r = ctx.app_res_folder
        b = int(ctx.ble_en)
        p = '{}/img_blue_color.png'.format(r)
        if not b:
            p = '{}/img_blue.png'.format(r)
        self.img_ble.setPixmap(QPixmap(p))
        s = 'GUI: secret BLE tap {}'.format(b)
        c_log.debug(s)

    def click_icon_gps(self, _):
        """ clicking shift + GPS icon adjusts DDH brightness :) """

        s = 'GUI: secret GPS tap {}'.format(self.bright_idx)
        c_log.debug(s)

        if linux_is_rpi():
            self.bright_idx = (self.bright_idx + 1) % 3
            v = self.bright_idx
            rpi_set_brightness(v)

    def click_icon_net(self, ev):
        """ clicking shift + NET icon (un)shows the EDIT tab """

        ev.accept()
        s = 'GUI: secret NET click, shift pressed = {}'
        c_log.debug(s.format(self.key_shift))

        if not self.key_shift:
            return
        self.key_shift = 0

        # toggle edit tab visibility
        teh = self.tab_edit_hide = not self.tab_edit_hide
        hide_edit_tab(self) if teh else show_edit_tab(self)

    def click_btn_purge_dl_folder(self):
        """ deletes contents in 'download files' folder """

        s = 'sure to empty dl_files folder?'
        if not _confirm_by_user(s):
            return

        # proceed to deletion
        d = pathlib.Path(ctx.app_dl_folder)
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

    def click_btn_purge_his_db(self):
        """ deletes contents in history database """

        s = 'sure to purge history?'
        if _confirm_by_user(s):
            db = DBHis(ctx.db_his)
            db.delete_all_records()
            delete_color_mac_file(ctx.db_color_macs)

        # show new (empty) history tab
        populate_history_tab(self)

    def click_btn_load_current_json_file(self):
        """ updates EDIT tab from current 'ddh.json' file """

        j = ctx.app_json_file
        ves = json_get_ship_name(j)
        f_t = json_get_forget_time_secs(j)
        self.lne_vessel.setText(ves)
        self.lne_forget.setText(str(f_t))

    def click_btn_err_gotcha(self):
        hide_error_tab(self)
        self.tabs.setCurrentIndex(0)

    def closeEvent(self, event):
        event.accept()
        c_log.debug('SYS: closing GUI ...')
        sys.stderr.close()
        os._exit(0)

    def keyPressEvent(self, e):
        """ controls status of the PRESS event of keyboard keys """

        if e.key() == Qt.Key_Shift:
            self.key_shift = 1

        known_keys = (Qt.Key_1, Qt.Key_3, Qt.Key_Shift)
        if e.key() not in known_keys:
            # this may fire with alt + tab too
            e = 'GUI: unknown keypress'
            c_log.debug(e)
            return

        # prevent div by zero
        number_keys = (Qt.Key_1, Qt.Key_3)
        if e.key() in number_keys and not self.plt_folders:
            c_log.debug('GUI: no data folders')
            e = 'no folders to plot'
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

        # build args needed by th_plot
        ax = self.plt_cnv.axes
        ts = self.plt_ts
        met = self.plt_metrics
        d = self.plt_dir
        plt_args = (d, ax, ts, met)
        self.qpo.put(plt_args, timeout=1)


def on_ctrl_c(signal_num, _):
    c_log.debug('SYS: captured signal {}'.format(signal_num))
    os._exit(signal_num)


def _aws_credentials_check():
    if ctx.aws_en:
        aws_credentials_assert()


def _sudo_permissions_check():
    if not 'SUDO_UID' in os.environ.keys():
        print('bluetooth requires root permissions')
        os._exit(1)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
