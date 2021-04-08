from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QDesktopWidget, QWidget, QMessageBox, QTableWidgetItem, \
    QHeaderView
from gpiozero import Button
from ddh.settings import ctx
from ddh.db.db_his import DBHis
from ddh.settings.version import VER_SW
from ddh.threads.th_time import ButtonPressEvent
from ddh.threads.utils import json_get_ship_name
from ddh.threads.utils_gps_quectel import utils_gps_in_land, utils_gps_valid_cache, utils_gps_backup_get
from mat.utils import linux_is_rpi, linux_is_docker_on_rpi


def setup_view(my_win, j):
    """ fills window with titles and default contents """
    a = my_win
    a.setupUi(a)
    a.setWindowTitle('Lowell Instruments\' Deck Data Hub')
    a.lbl_plt_bsy.setVisible(False)
    a.lbl_plt_msg.setVisible(False)
    a.tabs.setTabIcon(0, QIcon('ddh/gui/res/icon_info.png'))
    a.tabs.setTabIcon(1, QIcon('ddh/gui/res/icon_graph.ico'))
    a.tabs.setTabIcon(2, QIcon('ddh/gui/res/icon_history.ico'))
    a.tabs.setTabIcon(3, QIcon('ddh/gui/res/icon_setup.png'))
    a.setWindowIcon(QIcon('ddh/gui/res/icon_lowell.ico'))
    a.img_ble.setPixmap(QPixmap('ddh/gui/res/img_blue_color.png'))
    a.img_gps.setPixmap(QPixmap('ddh/gui/res/img_gps_dis.png'))
    a.img_plt.setPixmap(QPixmap('ddh/gui/res/img_plot_color.png'))
    a.img_net.setPixmap(QPixmap('ddh/gui/res/img_sync_color.png'))
    a.img_boat.setPixmap(QPixmap('ddh/gui/res/img_boatname_color.png'))
    ship = json_get_ship_name(j)
    a.lbl_boatname.setText(ship)
    a.setCentralWidget(a.tabs)
    a.tabs.setCurrentIndex(0)
    a.vl_3.addWidget(a.plt_cnv)
    a.lbl_ver.setText('DDH v{}'.format(VER_SW))
    fmt = '{}\n{}\n{}\n{}'
    a.lbl_time_n_pos.setText(fmt.format('', '', '', ''))
    fmt = '{}\n{}'
    a.lbl_net_n_cloud.setText(fmt.format('', ''))
    fmt = '{}\n{}\n{}'
    a.lbl_plot.setText(fmt.format('', '', ''))
    return a


def setup_his_tab(my_app):
    """ fills history tab"""

    a = my_app
    a.tbl_his.clear()

    # update with latest results
    db = DBHis(ctx.db_his)
    r = db.get_recent_records()
    for i, h in enumerate(r):
        mac, sn = h[1], h[2]
        lat, lon, ts = h[3], h[4], h[5]
        it = QTableWidgetItem(sn)
        it.setToolTip(mac)
        a.tbl_his.setItem(i, 0, it)
        s = '{},{}'.format(lat, lon)
        a.tbl_his.setItem(i, 1, QTableWidgetItem(s))
        # 2021/03/01 14:56:34 -> '21/03/01 14:56'
        a.tbl_his.setItem(i, 2, QTableWidgetItem(ts[2:-3]))
    a.tbl_his.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    labels = ['serial num', 'last position', 'last time']
    a.tbl_his.setHorizontalHeaderLabels(labels)


def populate_history_tab(self):
    setup_his_tab(self)


def setup_window_center(my_app):
    """ on RPi, DDH app uses full screen """
    a = my_app

    if linux_is_rpi() or linux_is_docker_on_rpi():
        a.showFullScreen()

    # get window + screen shape, match both, adjust upper left corner
    r = a.frameGeometry()
    c = QDesktopWidget().availableGeometry().center()
    r.moveCenter(c)
    a.move(r.topLeft())


def setup_buttons_gui(my_app):
    """ link buttons and labels clicks and signals """
    a = my_app

    # labels' event connections
    a.img_boat.mousePressEvent = a.click_icon_boat
    a.img_ble.mousePressEvent = a.click_icon_ble
    a.img_gps.mousePressEvent = a.click_icon_gps
    a.img_net.mousePressEvent = a.click_icon_net
    a.img_plt.mousePressEvent = a.click_icon_plot

    # buttons' connections
    a.btn_known_clear.clicked.connect(a.click_btn_clear_known_mac_list)
    a.btn_see_all.clicked.connect(a.click_btn_clear_see_all_macs)
    a.btn_see_cur.clicked.connect(a.click_btn_see_macs_in_current_json_file)
    a.btn_arrow.clicked.connect(a.click_btn_arrow_move_entries)
    a.btn_setup_apply.clicked.connect(a.click_btn_apply_write_json_file)
    a.btn_dl_purge.clicked.connect(a.click_btn_purge_dl_folder)
    a.btn_his_purge.clicked.connect(a.click_btn_purge_his_db)
    a.btn_load_current.clicked.connect(a.click_btn_load_current_json_file)
    a.btn_err_gotcha.clicked.connect(a.click_btn_err_gotcha)


def connect_gui_signals_n_slots(my_app):
    a = my_app
    a.sig_boot.status.connect(a.slot_status)
    a.sig_ble.status.connect(a.slot_status)
    a.sig_gps.status.connect(a.slot_status)
    a.sig_cnv.status.connect(a.slot_status)
    a.sig_net.status.connect(a.slot_status)
    a.sig_plt.status.connect(a.slot_status)
    a.sig_aws.status.connect(a.slot_status)
    a.sig_tim.status.connect(a.slot_status)
    a.sig_boot.error.connect(a.slot_error)
    a.sig_gps.error.connect(a.slot_error)
    a.sig_cnv.error.connect(a.slot_error)
    a.sig_plt.error.connect(a.slot_error)
    a.sig_ble.error.connect(a.slot_error)
    a.sig_aws.error.connect(a.slot_error)
    a.sig_cnv.update.connect(a.slot_gui_update_cnv)
    a.sig_gps.update.connect(a.slot_gui_update_gps_pos)
    a.sig_tim.update.connect(a.slot_gui_update_time)
    a.sig_net.update.connect(a.slot_gui_update_net_source)
    a.sig_plt.update.connect(a.slot_gui_update_plt)
    a.sig_aws.update.connect(a.slot_gui_update_aws)
    a.sig_plt.start.connect(a.slot_plt_start)
    a.sig_plt.msg.connect(a.slot_plt_msg)
    a.sig_plt.end.connect(a.slot_plt_end)
    a.sig_plt.debug.connect(a.slot_debug)
    a.sig_ble.debug.connect(a.slot_debug)
    a.sig_ble.scan_pre.connect(a.slot_ble_scan_pre)
    a.sig_ble.session_pre.connect(a.slot_ble_session_pre)
    a.sig_ble.logger_pre.connect(a.slot_ble_logger_pre)
    a.sig_ble.file_pre.connect(a.slot_ble_file_pre)
    a.sig_ble.file_post.connect(a.slot_ble_file_post)
    a.sig_ble.logger_post.connect(a.slot_ble_logger_post)
    a.sig_ble.session_post.connect(a.slot_ble_session_post)
    a.sig_ble.deployed.connect(a.slot_his_update)
    a.sig_ble.dl_step.connect(a.slot_ble_dl_step)
    a.sig_ble.dl_warning.connect(a.slot_ble_dl_warning)
    a.sig_ble.gps_bad.connect(a.slot_ble_gps_bad)
    a.sig_ble.logger_plot_req.connect(a.slot_ble_logger_plot_req)
    a.sig_tim.via.connect(a.slot_gui_update_time_source)


def paint_gps_icon_w_color_land_sea(my_app, lat, lon):
    """ paints the gps icon """

    a = my_app
    if utils_gps_in_land(lat, lon):
        img = 'ddh/gui/res/img_gps_land.png'
        a.img_gps.setPixmap(QPixmap(img))
        return
    img = 'ddh/gui/res/img_gps_sea.png'
    a.img_gps.setPixmap(QPixmap(img))


def paint_gps_icon_w_color_dis_or_cache(my_app):
    """ paints the gps icon as disabled or cache """

    a = my_app
    if utils_gps_valid_cache():
        # dirty but meh, update GUI content
        lat, lon, _ = utils_gps_backup_get()
        img = 'ddh/gui/res/img_gps_cache.png'
        cc = a.lbl_time_n_pos.text().split('\n')
        lat = '{:+.6f}'.format(float(lat))
        lon = '{:+.6f}'.format(float(lon))
        s = '{}\n{}\n{}\n{}'.format(cc[0], lat, lon, cc[3])
        a.lbl_time_n_pos.setText(s)
    else:
        img = 'ddh/gui/res/img_gps_dis.png'
    a.img_gps.setPixmap(QPixmap(img))


def hide_edit_tab(ui):
    # find tab ID, index and keep ref
    p = ui.tabs.findChild(QWidget, 'tab_setup')
    i = ui.tabs.indexOf(p)
    ui.tab_edit_wgt_ref = ui.tabs.widget(i)
    ui.tabs.removeTab(i)


def show_edit_tab(ui):
    icon = QIcon('ddh/gui/res/icon_setup.png')
    ui.tabs.addTab(ui.tab_edit_wgt_ref, icon, ' Setup')
    p = ui.tabs.findChild(QWidget, 'tab_setup')
    i = ui.tabs.indexOf(p)
    ui.tabs.setCurrentIndex(i)


def hide_error_tab(ui):
    p = ui.tabs.findChild(QWidget, 'tab_err')
    i = ui.tabs.indexOf(p)
    ui.tab_err_wgt_ref = ui.tabs.widget(i)
    ui.tabs.removeTab(i)


def show_error_tab(ui):
    icon = QIcon('ddh/gui/res/icon_lowell.png')
    ui.tabs.addTab(ui.tab_err_wgt_ref, icon, ' Note')
    p = ui.tabs.findChild(QWidget, 'tab_err')
    i = ui.tabs.indexOf(p)
    ui.tabs.setCurrentIndex(i)


def dict_from_list_view(l_v):
    """ grab listview entries 'name mac' and build a dict """
    d = dict()
    n = l_v.count()
    for _ in range(n):
        it = l_v.item(_)
        pair = it.text().split()
        d[pair[0]] = pair[1]
    return d


def setup_buttons_rpi(my_app, c_log):
    """ link raspberry buttons with callback functions """

    a = my_app
    if not linux_is_rpi():
        c_log.debug('SYS: not a raspberry system')
        return

    def button1_pressed_cb():
        a.keyPressEvent(ButtonPressEvent(Qt.Key_1))

    def button2_pressed_cb():
        a.keyPressEvent(ButtonPressEvent(Qt.Key_2))

    # upon release, check it was a press or a hold
    def button3_held_cb():
        a.btn_3_held = 1

    def button3_released_cb():
        if a.btn_3_held:
            a.keyPressEvent(ButtonPressEvent(Qt.Key_6))
        else:
            a.keyPressEvent(ButtonPressEvent(Qt.Key_3))
        a.btn_3_held = 0

    a.button1 = Button(16, pull_up=True)
    a.button2 = Button(20, pull_up=True)
    a.button3 = Button(21, pull_up=True)
    a.button1.when_pressed = button1_pressed_cb
    a.button2.when_pressed = button2_pressed_cb
    a.button3.when_held = button3_held_cb
    a.button3.when_released = button3_released_cb


def _confirm_by_user(s):
    """ ask user to press OK or CANCEL """

    m = QMessageBox()
    m.setIcon(QMessageBox.Information)
    m.setWindowTitle('warning')
    m.setText(s)
    choices = QMessageBox.Ok | QMessageBox.Cancel
    m.setStandardButtons(choices)
    return m.exec_() == QMessageBox.Ok
