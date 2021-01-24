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
from ddh.threads.utils_gps_internal import gps_in_land
from mat.utils import linux_is_rpi, linux_is_docker_on_rpi


def setup_view(my_win, j):
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
        a.tbl_his.setItem(i, 2, QTableWidgetItem(ts[:14]))
    a.tbl_his.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    labels = ['serial num', 'last position', 'last time']
    a.tbl_his.setHorizontalHeaderLabels(labels)


def populate_history_tab(self):
    setup_his_tab(self)


def setup_window_center(my_app):
    a = my_app

    if linux_is_rpi() or linux_is_docker_on_rpi():
        # on RPi, use full screen
        a.showFullScreen()

    # get window + screen shape, match both, adjust upper left corner
    r = a.frameGeometry()
    c = QDesktopWidget().availableGeometry().center()
    r.moveCenter(c)
    a.move(r.topLeft())


def setup_buttons_gui(my_app):
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


def update_gps_icon_land_sea(my_app, did_ok, lat, lon):
    a = my_app
    if not did_ok:
        img = 'ddh/gui/res/img_gps_dis.png'
        a.img_gps.setPixmap(QPixmap(img))
        return
    if gps_in_land(lat, lon):
        img = 'ddh/gui/res/img_gps_land.png'
        a.img_gps.setPixmap(QPixmap(img))
        return
    img = 'ddh/gui/res/img_gps_sea.png'
    a.img_gps.setPixmap(QPixmap(img))


def hide_edit_tab(ui):
    # find tab ID, index and keep ref
    p = ui.tabs.findChild(QWidget, 'tab_setup')
    i = ui.tabs.indexOf(p)
    ui.tab_edit_wgt_ref = ui.tabs.widget(i)
    ui.tabs.removeTab(i)


def dict_from_list_view(l_v):
    d = dict()
    n = l_v.count()
    for _ in range(n):
        it = l_v.item(_)
        pair = it.text().split()
        d[pair[0]] = pair[1]
    return d


def setup_buttons_rpi(my_app, c_log):
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
    m = QMessageBox()
    m.setIcon(QMessageBox.Information)
    m.setWindowTitle('warning')
    m.setText(s)
    choices = QMessageBox.Ok | QMessageBox.Cancel
    m.setStandardButtons(choices)
    return m.exec_() == QMessageBox.Ok
