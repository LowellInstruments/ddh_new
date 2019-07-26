from sortedcontainers import SortedDict
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


def linux_set_time_from_gps(when):
    # timedatectl is command line to stop systemd-timesyncd.service
    time_string = datetime(*when).isoformat()
    subprocess.call(shlex.split('sudo timedatectl set-ntp false'))
    subprocess.call(shlex.split("sudo date -s '%s'" % time_string))

    # raspberry has no RTC so avoid the following
    # subprocess.call(shlex.split('sudo hwclock -w'))


def linux_set_time_to_use_ntp():
    # if calling this after assuring internet connectivity, we should be ok
    subprocess.call(shlex.split('timedatectl set-ntp true'))


# see if there is an internet connection
def have_internet_connection():
    conn = http.client.HTTPConnection('www.google.com', timeout=3)
    try:
        conn.request('HEAD', '/')
        conn.close()
        return True
    except (http.client.CannotSendRequest, socket.gaierror, ConnectionError):
        conn.close()
        return False


def get_last_key_from_dict(input_dict):
    if input_dict:
        return list(input_dict.keys())[-1]
    return None


def get_first_key_from_dict(input_dict):
    if input_dict:
        return list(input_dict.keys())[0]
    return None


def get_start_key_from_end_key(end_key, before):
    # logger output is w/o tzinfo but microsecond information
    if end_key:
        calc_time = iso8601.parse_date(end_key) - timedelta(hours=before)
        calc_time = calc_time.replace(tzinfo=None).isoformat() + '.000'
        return calc_time
    return None


def slice_bw_keys(start_key, end_key, input_dict):
    start_index = input_dict.bisect_left(start_key)
    # next line bisect_left excludes, bisect_right includes edge element
    end_index = input_dict.bisect_left(end_key)
    output_data_keys = list(input_dict.keys())[start_index:end_index]
    output_data_values = list(input_dict.values())[start_index:end_index]
    output_dict = SortedDict(zip(output_data_keys, output_data_values))
    return output_dict


# discard file names not ending 'filter' string
def filter_files_by_name_ending(input_list, name_ending):
    output_list = []
    for each_name in input_list:
        if each_name.endswith(name_ending):
            output_list.append(each_name)
    return output_list


# discard files shorter than size bytes, 2000 are about 60 rows
def filter_files_by_size(input_list, minimum_size):
    output_list = []
    for each_name in input_list:
        try:
            if os.path.getsize(each_name) > minimum_size:
                output_list.append(each_name)
        except FileNotFoundError:
            pass
    return output_list


# recursively collect all logger files w/ indicated extension
def list_files_by_extension(dir_name, extension):
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
    print('---> detect_raspberry() failed')
    return False


def get_span_as_hh_mm(word):
    if word == 'hour':
        return 1, 60
    if word == 'day':
        return 24, 24 * 60
    if word == 'week':
        return 168, 168 * 60
    if word == 'month':
        return 730, 730 * 60
    if word == 'year':
        return 8765, 8765 * 60


def get_span_as_slices(word):
    if word == 'hour':
        return 60  # or 30 if less resolution but faster
    if word == 'day':
        return 24
    if word == 'week':
        return 7
    if word == 'month':
        return 30
    if word == 'year':
        return 12


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
    except (FileNotFoundError, TypeError):
        return 'Unnamed ship'
