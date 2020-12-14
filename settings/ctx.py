import sys
import socket


# constants
import threading


PLT_SHOW_TIMEOUT = 120
PLT_MSG_TIMEOUT = 5


# set at main.py, shared stuff
app_root_folder = None
app_res_folder = None
dl_folder = None
app_conf_folder = None
app_logs_folder = None
json_file = None
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


# FTP: current and start states + switch capability
aws_en = True
sw_ftp_en = True


# BLE: current and start states + switch capability
ble_en = True
sw_ble_en = True
macs_lists_persistent = True


def only_one_instance(name):
    # hold a ref or garbage collector makes all this not work
    ooi = only_one_instance
    ooi._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    try:
        # '\0' so the lock does not take a filesystem entry
        ooi._lock_socket.bind('\0' + name)
    except socket.error:
        s = '{} already running so NOT executing this one'
        print(s.format(name))
        sys.exit(1)
