import os
import socket


# constants
PLT_SHOW_TIMEOUT = 120
PLT_MSG_TIMEOUT = 5


# shared stuff
app_root_folder = None
dl_files_folder = None
app_conf_folder = None
json_file = None
span_dict = None
db_plt = None
db_his = None
init_ok = False


# current logger context
lg_name = ''
lg_num = ''
lg_dl_size = 0
lg_dl_pc = 0
lg_hci = 0


# FTP: current and start states + switch capability
ftp_ongoing = False
ftp_en = True
sw_ftp_en = True


# BLE: current and start states + switch capability
ble_ongoing = False
ble_en = True
sw_ble_en = False


# PLT: current state
plt_ongoing = False


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
        os._exit(1)
