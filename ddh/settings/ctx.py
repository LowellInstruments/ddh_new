import sys
import socket
import threading


# messagebox timeout constants
PLT_SHOW_TIMEOUT = 120
PLT_MSG_TIMEOUT = 5


# set at main.py
app_res_folder = None
app_dl_folder = None
app_conf_folder = None
app_logs_folder = None
app_json_file = None
plt_units = None
span_dict = None
db_plt = None
db_his = None
db_color_macs = None


# current logger context
lg_dl_size = 0
lg_dl_bar_pc = 0


# semaphores
sem_aws = threading.Lock()
sem_ble = threading.Lock()
sem_plt = threading.Lock()


# AWS: enabled or not
aws_en = True


# BLE: enabled or not + switch capability
ble_en = True
sw_ble_en = True


# cell shield: present or not
cell_shield_en = True


# debug hooks :)
dbg_hook_purge_mac_blacklist_on_boot = False
dbg_hook_purge_dl_files_for_this_mac = False
dbg_hook_make_dummy_ti_logger_visible = False
dbg_hook_make_gps_give_fake_measurement = False
dbg_hook_make_ntp_to_fail = False


def only_one_instance(name):
    """ ensures only 1 DDH program runs at a given time """

    ooi = only_one_instance
    ooi._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    try:
        # '\0' so the lock does not take a filesystem entry
        ooi._lock_socket.bind('\0' + name)

    except socket.error:
        s = '{} already running so NOT executing this one'
        print(s.format(name))
        sys.exit(1)
