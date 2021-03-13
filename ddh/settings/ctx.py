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
db_blk = None
db_ong = None


# current logger context
lg_num = ''
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


# APP behavior modifier
macs_blacklist_pre_rm = True
dummy_ti_logger = False
dummy_gps = True
pre_rm_files = True


def only_one_instance(name):
    """ ensures only one DDH program running"""
    ooi = only_one_instance
    ooi._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    try:
        # '\0' so the lock does not take a filesystem entry
        ooi._lock_socket.bind('\0' + name)
    except socket.error:
        s = '{} already running so NOT executing this one'
        print(s.format(name))
        sys.exit(1)
