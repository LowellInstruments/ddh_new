from datetime import (
    datetime,
    timedelta
)
import http.client
import subprocess
import iso8601
import shlex
import socket
import os
import glob
from logzero import logger as console_log
from mat.data_converter import DataConverter, default_parameters
import dask.dataframe as dd


def linux_set_time_from_gps(when):
    # timedatectl: UNIX command to stop systemd-timesyncd.service
    time_string = datetime(*when).isoformat()
    subprocess.call(shlex.split('sudo timedatectl set-ntp false'))
    subprocess.call(shlex.split("sudo date -s '%s'" % time_string))

    # raspberry has no RTC so avoid the following
    # subprocess.call(shlex.split('sudo hwclock -w'))


def linux_set_time_to_use_ntp():
    subprocess.call(shlex.split('sudo timedatectl set-ntp true'))


def have_internet_connection():
    conn = http.client.HTTPConnection('www.google.com', timeout=3)
    try:
        conn.request('HEAD', '/')
        conn.close()
        return True
    except (http.client.CannotSendRequest, socket.gaierror, ConnectionError):
        conn.close()
        return False


# recursively collect all logger files w/ indicated extension
def list_files_by_extension_in_dir(dir_name, extension):
    if not dir_name: return []
    if os.path.isdir(dir_name):
        wildcard = dir_name + '/**/*.' + extension
        return glob.glob(wildcard, recursive=True)


# recursively remove all files w/ indicated extension
def rm_files_by_extension(dir_name, extension):
    if os.path.isdir(dir_name):
        for filename in list_files_by_extension(dir_name, extension):
            os.remove(filename)


# be sure we are up-to-date with downloaded logger folders
def update_dl_folder_list():
    dl_root_folder = 'dl_files'
    if os.path.isdir(dl_root_folder):
        output_list = [f.path for f in os.scandir(dl_root_folder) if f.is_dir()]
        return output_list
    else:
        os.makedirs(dl_root_folder, exist_ok=True)


def detect_raspberry():
    node_name = os.uname()[1]
    if node_name.endswith('raspberrypi') or node_name.startswith('rpi'):
        return True
    return False


def check_config_file():
    import json
    try:
        with open('ddh.json') as f:
            json.load(f)
    except (FileNotFoundError, TypeError, json.decoder.JSONDecodeError):
        console_log.error('SYS: error reading ddh.json config file')
        return False
    return True


def get_ship_name():
    import json
    try:
        with open('ddh.json') as f:
            ddh_cfg_string = json.load(f)
            return ddh_cfg_string['ship_info']['name']
    except TypeError:
        return 'Unnamed ship'


def get_metrics():
    import json
    with open('ddh.json') as f:
        ddh_cfg_string = json.load(f)
        return ddh_cfg_string['metrics']


def extract_mac_from_folder(d):
    try:
        return d.split('/')[1].replace('-', ':')
    except (ValueError, Exception):
        return None


def convert_lid_files_to_csv(two_folders_list):
    d1, d2 = two_folders_list
    if not os.path.exists(d1): return None
    l1 = list_files_by_extension_in_dir(d1, 'lid')
    l2 = list_files_by_extension_in_dir(d2, 'lid')

    # convert LID files to CSV
    parameters = default_parameters()
    for f in l1: DataConverter(f, parameters).convert()
    for f in l2: DataConverter(f, parameters).convert()


def convert_csv_to_data_frames(dirs, metric):
    # convert 'Temperature (C)' to just 'Temperature'
    metric = metric.split(' ')[0]

    ddf1, ddf2 = None, None
    try:
        ddf1 = dd.read_csv(os.path.join(dirs[0], "*" + metric + "*.csv"))
    except (IOError, Exception):
        return None
    try:
        ddf2 = dd.read_csv(os.path.join(dirs[1], "*" + metric + "*.csv"))
    except (IOError, Exception):
        pass
    return ddf1, ddf2


def translate_logger_name(logger_mac):
    import json
    name = 'unnamed_logger'
    try:
        with open('ddh.json') as f:
            ddh_cfg_string = json.load(f)
            name = ddh_cfg_string['db_logger_macs'][logger_mac]
    except (FileNotFoundError, TypeError, KeyError):
        pass
    return name

