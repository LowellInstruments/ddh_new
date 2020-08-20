import datetime
import pathlib
import shutil
import matplotlib
import sys
import time
from context import ctx
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
    QFileDialog)

from gui import utils_gui
from gui.utils_gui import (
    setup_view, setup_his_tab, setup_buttons_gui, setup_window_center, hide_edit_tab,
    dict_from_list_view, setup_buttons_rpi, _confirm_by_user, update_gps_icon)
from threads import th_life, th_gps, th_ble, th_plt, th_ftp, th_net, th_cnv
from settings.conf import yaml_load_pairs, json_gen_ddh
from threads.th import DDHThread
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from db.db_his import DBHis
from threads.utils import (
    update_dl_folder_list,
    linux_rpi,
    json_get_ship_name,
    json_get_metrics,
    linux_set_ntp,
    json_get_macs,
    json_mac_dns,
    json_get_forget_time_secs, json_get_span_dict, rpi_set_brightness, json_get_hci_if, setup_db_n_logs, json_get_pairs)
from logzero import logger as c_log
from threads.sig import (
    SignalsBLE,
    SignalsPLT,
    SignalsLife, SignalsGPS, SignalsFTP, SignalsNET, SignalsCNV)
import os
import gui.designer_main as d_m
matplotlib.use('Qt5Agg')
if linux_rpi():
    pass


class DDHQtApp(QMainWindow, d_m.Ui_MainWindow):

    def __init__(self, *args, **kwargs):
        # context checks
        assert ctx.init_ok

        # load configuration in json / yaml file
        j = ctx.json_file
        ctx.lg_hci = json_get_hci_if(j)
        ctx.span_dict = json_get_span_dict(j)
        setup_db_n_logs()

        # gui: view
        super(DDHQtApp, self).__init__(*args, **kwargs)
        self.plt_cnv = MplCanvas(self, width=5, height=3, dpi=100)
        setup_view(self, j)
        setup_buttons_gui(self)
        setup_his_tab(self)
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
        self.plt_metrics = json_get_metrics(j)
        self.bright_idx = 2
        self.btn_3_held = 0
        self.tab_edit_hide = True
        self.tab_edit_wgt_ref = None
        self.key_shift = None
        hide_edit_tab(self)
        self._populate_history_tab()

        # threads
        self.th_ble = None
        self.th_gps = None
        self.th_plt = None
        self.th_life = None
        self.th_ftp = None
        self.th_net = None
        self.th_cnv = None
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(7)
        self._create_threads()
        self.thread_pool.start(self.th_life)
        self.thread_pool.start(self.th_gps)
        self.thread_pool.start(self.th_ble)
        self.thread_pool.start(self.th_ftp)
        self.thread_pool.start(self.th_net)
        self.thread_pool.start(self.th_cnv)

        # timer used to quit this app
        self.tim_q = QTimer()
        self.tim_q.timeout.connect(self._timer_bye)

    def _timer_bye(self):
        self.tim_q.stop()
        os._exit(0)

    def _click_icon_clock(self, _):
        c_log.debug('GUI: clicked secret bye!')
        self.closeEvent(_)

    def _click_btn_known_clear(self):
        self.lst_mac_org.clear()
        self.lst_mac_dst.clear()

    def _click_btn_see_all(self):
        # loads (mac, name) pairs from yaml file
        self.lst_mac_org.clear()
        r = str(ctx.app_conf_folder)
        f = QFileDialog.getOpenFileName(QFileDialog(),
                                        'Choose file', r,
                                        "YAML files (*.yml)")
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
        finally:
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

    def _click_icon_cloud(self, _):
        # requires shift key
        if not self.key_shift:
            return

        if not ctx.sw_ftp_en:
            return

        ctx.ftp_en = not ctx.ftp_en
        f = int(ctx.ftp_en)
        if f:
            p = 'gui/res/img_upload_color.png'
        else:
            p = 'gui/res/img_upload.png'
        self.img_cloud.setPixmap(QPixmap(p))
        s = 'GUI: secret UPL toggle {}'.format(f)
        c_log.debug(s)

    def _click_icon_output(self, _):
        # requires shift key
        if not self.key_shift:
            return
        self.showMinimized()

    def _click_icon_ble(self, _):
        # allow to click or not
        if not ctx.sw_ble_en:
            return

        ctx.ble_en = not ctx.ble_en
        b = int(ctx.ble_en)
        if b:
            p = 'gui/res/img_blue_color.png'
        else:
            p = 'gui/res/img_blue.png'
        self.img_ble.setPixmap(QPixmap(p))
        s = 'GUI: secret BLE toggle {}'.format(b)
        c_log.debug(s)

    def _click_icon_gps(self, _):
        s = 'GUI: secret GPS click {}'.format(self.bright_idx)
        c_log.debug(s)

        if linux_rpi():
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
        self._populate_history_tab()

    def _click_btn_load_current(self):
        j = ctx.json_file
        ves = json_get_ship_name(j)
        f_t = json_get_forget_time_secs(j)
        self.lne_vessel.setText(ves)
        self.lne_forget.setText(str(f_t))

    def _create_threads(self):
        # life
        self.th_life = DDHThread(th_life.fxn, SignalsLife)
        self.th_life.signals().lif_beat.connect(self.slot_beat)
        self.th_life.signals().lif_status.connect(self.slot_status)

        # ble
        k = json_get_macs(ctx.json_file)
        ft_s = json_get_forget_time_secs(ctx.json_file)
        h = ctx.lg_hci
        arg = [ft_s, 60, k, h]
        self.th_ble = DDHThread(th_ble.fxn, SignalsBLE, arg)
        self.th_ble.signals().ble_scan_pre.connect(self.slot_ble_scan_pre)
        self.th_ble.signals().ble_scan_post.connect(self.slot_ble_scan_post)
        self.th_ble.signals().ble_session_pre.connect(self.slot_ble_session_pre)
        self.th_ble.signals().ble_session_post.connect(self.slot_ble_session_post)
        self.th_ble.signals().ble_logger_pre.connect(self.slot_ble_logger_pre)
        self.th_ble.signals().ble_logger_post.connect(self.slot_ble_logger_post)
        self.th_ble.signals().ble_file_pre.connect(self.slot_ble_file_pre)
        self.th_ble.signals().ble_file_post.connect(self.slot_ble_file_post)
        self.th_ble.signals().ble_status.connect(self.slot_status)
        self.th_ble.signals().ble_error.connect(self.slot_error)
        self.th_ble.signals().ble_warning.connect(self.slot_warning)
        self.th_ble.signals().ble_deployed.connect(self.slot_his_update)
        self.th_ble.signals().ble_dl_step.connect(self.slot_ble_dl_step)
        self.th_ble.signals().ble_logger_plot_req.connect(self.slot_ble_logger_plot_req)

        # gps
        self.th_gps = DDHThread(th_gps.fxn, SignalsGPS)
        self.th_gps.signals().gps_status.connect(self.slot_status)
        self.th_gps.signals().gps_error.connect(self.slot_error)
        self.th_gps.signals().gps_result.connect(self.slot_gps_result)
        self.th_gps.signals().gps_update.connect(self.slot_gps_update)

        # ftp
        self.th_ftp = DDHThread(th_ftp.fxn, SignalsFTP)
        self.th_ftp.signals().ftp_conn.connect(self.slot_ftp_conn)
        self.th_ftp.signals().ftp_error.connect(self.slot_error)
        self.th_ftp.signals().ftp_status.connect(self.slot_status)

        # network
        self.th_net = DDHThread(th_net.fxn, SignalsNET)
        self.th_net.signals().net_status.connect(self.slot_status)
        self.th_net.signals().net_rv.connect(self.slot_net_rv)

        # conversion
        self.th_cnv = DDHThread(th_cnv.fxn, SignalsCNV)
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

    @pyqtSlot(str, name='slot_status')
    def slot_status(self, t):
        c_log.info(t)

    @pyqtSlot(str, name='slot_warning')
    def slot_warning(self, e):
        c_log.warning(e)
        self.lbl_out.setText(e)

    @pyqtSlot(str, name='slot_error')
    def slot_error(self, e):
        c_log.error(e)

    @pyqtSlot(str, name='slot_ftp_conn')
    def slot_ftp_conn(self, c):
        c_log.info(c)
        self.lbl_cloud.setText(c)

    @pyqtSlot(str, name='slot_ble_scan_pre')
    def slot_ble_scan_pre(self, s):
        i = 'gui/res/img_blue.png'
        if ctx.ble_en:
            i = 'gui/res/img_blue_color.png'
        self.img_ble.setPixmap(QPixmap(i))
        self.bar_dl.setValue(0)
        self.lbl_ble.setText(s)

    @pyqtSlot(object, name='slot_ble_scan_post')
    def slot_ble_scan_post(self, result):
        t = self.lbl_ble.text()
        if t.startswith('connected'):
            t = 'connected\n{} loggers found'.format(len(result))
            self.lbl_ble.setText(t)

    # a download session consists of 1 to n loggers
    @pyqtSlot(str, int, int, name='slot_ble_session_pre')
    def slot_ble_session_pre(self, desc, val_1, val_2):
        # desc: mac, val_1: logger index, val_2: total num of loggers
        t = 'logger {} of {} '.format(val_1, val_2)
        ctx.lg_num = t
        t = 'connected\n{}'.format(t)
        self.lbl_ble.setText(t)
        j = ctx.json_file
        t = 'logger\n\'{}\''.format(json_mac_dns(j, desc))
        self.lbl_out.setText(t)

    # indicates current logger of current download session
    @pyqtSlot(name='slot_ble_logger_pre')
    def slot_ble_logger_pre(self):
        n = ctx.lg_num
        t = 'configuring\n{}'.format(n)
        self.lbl_ble.setText(t)
        ctx.lg_dl_size = 0
        ctx.lg_dl_pc = 0
        self.bar_dl.setValue(0)

    # one logger 1 to n files
    @pyqtSlot(str, int, int, int, int, name='slot_ble_file_pre')
    def slot_ble_file_pre(self, _, dl_s, val_1, val_2, val_3):
        # val_1: dl i, val_2: dl n, _: dl name, dl_s: dl size
        text = 'getting\n file {} of {}'.format(val_1, val_2)
        self.lbl_ble.setText(text)
        text = '{} minute(s)\nleft'.format(val_3)
        self.lbl_out.setText(text)
        ctx.lg_dl_size = dl_s

    @pyqtSlot(int, int, name='slot_ble_file_post')
    def slot_ble_file_post(self, _, speed):
        text = '{} B/s'.format(speed)
        self.lbl_out.setText(text)

    @pyqtSlot(str, name='slot_ble_logger_plot_req')
    def slot_ble_logger_plot_req(self, mac):
        if not mac:
            s = 'no plot from last logger'
            self.lbl_out.setText(s)
            return
        d = ctx.dl_files_folder
        self.plt_folders = update_dl_folder_list(d)
        d = pathlib.Path(ctx.dl_files_folder)
        d = d / str(mac).replace(':', '-')
        self.plt_dir = str(d)
        self._throw_th_plt()

    @pyqtSlot(int, name='slot_ble_logger_post')
    def slot_ble_logger_post(self, n):
        s = 'completed'
        self.lbl_ble.setText(s)
        if n > 0:
            s = 'got {} file(s)'.format(n)
        elif n == 0:
            s = 'no files to get'
        else:
            s = 'already had all files'
        self.lbl_out.setText(s)
        self.bar_dl.setValue(100)

    @pyqtSlot(str, name='slot_ble_session_post')
    def slot_ble_session_post(self, desc):
        self.lbl_out.setText(desc)

    @pyqtSlot(name='slot_ble_dl_step')
    def slot_ble_dl_step(self):
        # 128 is hardcoded XMODEM packet size
        pc = 100 * (128 / ctx.lg_dl_size)
        ctx.lg_dl_pc += pc
        self.bar_dl.setValue(ctx.lg_dl_pc)

    @pyqtSlot(name='slot_plt_start')
    def slot_plt_start(self):
        ctx.plt_ongoing = True
        self.lbl_out.setText('Plotting...')
        self.lbl_plt_bsy.setVisible(True)

    # display any successfully built plot
    @pyqtSlot(object, name='slot_plt_result')
    def slot_plt_result(self, result):
        if result:
            self.lbl_out.setText('plot ok')
            self.tabs.setCurrentIndex(1)
            to = ctx.PLT_SHOW_TIMEOUT
            self.plt_timeout_dis = to
        else:
            self.lbl_out.setText('plot not ok')
        ctx.plt_ongoing = False
        self.lbl_plt_bsy.setVisible(False)

    @pyqtSlot(str, name='slot_plt_msg')
    def slot_plt_msg(self, desc):
        self.lbl_plt_msg.setText(desc)
        self.lbl_plt_msg.setVisible(True)
        to = ctx.PLT_MSG_TIMEOUT
        self.plt_timeout_msg = to

    @pyqtSlot(str, str, str, str, name='slot_gps_result')
    def slot_gps_result(self, src, _, lat, lon):
        """ receives result of GPS time sync """

        self.lbl_clock_sync.setText(src + ' time')
        if src == 'gps':
            t = 'GPS: received RMC frame.\n'
            t += '\t-> {} US/Eastern time offset adjusted\n'.format(t)
            t += '\t-> lat {} lon {}'.format(lat, lon)
            c_log.info(t)

    @pyqtSlot(bool, str, str, name='slot_gps_update')
    def slot_gps_update(self, did_ok, lat, lon):
        update_gps_icon(self, did_ok, lat, lon)
        if did_ok:
            self.lbl_gps.setText(lat + ' N\n' + lon + ' W')
            t = 'GPS: updated lat, lon'.format(lat, lon)
            c_log.info(t)
        else:
            # piggybacked GPS error message in 'lat'
            e = lat
            self.lbl_gps.setText(e)
            c_log.info(e)

    @pyqtSlot(str, name='slot_net_rv')
    def slot_net_rv(self, src):
        self.lbl_internet.setText(src)
        src = src.replace('\n', '')
        c_log.info('{}'.format(src))

    @pyqtSlot(str, name='slot_beat')
    def slot_beat(self, desc):
        # update GUI widgets
        self.sys_secs += 1
        self.bsy_dots = desc
        time_format = '%m / %d / %y\n%H : %M : %S'
        formatted_time = datetime.datetime.now().strftime(time_format)
        self.lbl_clock_time.setText(formatted_time)
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
        if self.plt_timeout_msg > 0:
            self.plt_timeout_msg -= 1

        # things updated less often
        if self.sys_secs % 30 == 0:
            j = ctx.json_file
            s_n = json_get_ship_name(j)
            self.lbl_boatname.setText(s_n)

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

    def closeEvent(self, event):
        if linux_rpi():
            linux_set_ntp()
        event.accept()
        c_log.debug('SYS: closing GUI ...')
        # dirty but ok, we quit anyway
        time.sleep(1)
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
            e = 'GUI: unknown keypress'
            c_log.debug(e)
            return

        # prevent div by zero
        if not self.plt_folders:
            c_log.debug('GUI: no data folders')
            e = 'no data folders'
            self.lbl_out.setText(e)
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
    if linux_rpi():
        linux_set_ntp()
    os._exit(signal_num)


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
