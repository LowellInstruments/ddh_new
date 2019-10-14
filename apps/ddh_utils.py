import datetime
import http.client
import subprocess
import shlex
import socket
import os
import glob

import iso8601
from logzero import logger as console_log
from mat.data_converter import DataConverter, default_parameters
import dask.dataframe as dd
import pandas as pd
import numpy as np


span_dict = {
    # unit: slices,     mm / slice,     mm / unit,  format,     ticks skip
    'h':    [12,        5,              60,         '%H:%M',    1],
    'd':    [48,        30,             1440,       '%H',       2],
    'w':    [14,        720,            10080,      '%m/%d',    2],
    'm':    [31,        1440,           43800,      '%d',       1],
    'y':    [12,        43800,          525600,     '%b %y',    1]
}


def linux_set_time_from_gps(when):
    # timedatectl: UNIX command to stop systemd-timesyncd.service
    time_string = datetime.datetime(*when).isoformat()
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
    if not dir_name:
        return []
    if os.path.isdir(dir_name):
        wildcard = dir_name + '/**/*.' + extension
        return glob.glob(wildcard, recursive=True)


# recursively remove all files w/ indicated extension
def rm_files_by_extension(path, ext):
    if os.path.isdir(path):
        for filename in list_files_by_extension_in_dir(path, ext):
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


def all_lid_to_csv(two_folders_list):
    # grab all LID files in these two folders
    d1, d2 = two_folders_list
    if not os.path.exists(d1):
        return None
    l1 = list_files_by_extension_in_dir(d1, 'lid')
    l2 = list_files_by_extension_in_dir(d2, 'lid')

    # convert LID files to CSV
    parameters = default_parameters()
    for f in l1:
        DataConverter(f, parameters).convert()
    for f in l2:
        DataConverter(f, parameters).convert()


def csv_to_data_frames(dirs, metric):
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


def get_logger_name(logger_mac):
    import json
    name = 'unnamed_logger'
    try:
        with open('ddh.json') as f:
            ddh_cfg_string = json.load(f)
            name = ddh_cfg_string['db_logger_macs'][logger_mac]
    except (FileNotFoundError, TypeError, KeyError):
        pass
    return name


# returns last row time value as str
def df_last_time(df_in):
    # p pandas data frame, t numpy array
    p = df_in.tail(1)
    t = p['ISO 8601 Time'].values
    return str(t[0])


# returns first row time value as str
def df_first_time(df_in):
    p = df_in.head(1)
    t = p['ISO 8601 Time'].values
    return str(t[0])


# t is a string
def offset_time_mm(t, mm):
    a = datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.000')
    a += datetime.timedelta(minutes=mm)
    return a.strftime('%Y-%m-%dT%H:%M:%S.000')


# a and b are time strings
def _slice_w_idx(df_in, a, b, metric='Temperature (C)'):
    # compute() returns a panda series
    t = df_in['ISO 8601 Time'].compute()
    c = df_in[metric].compute()
    # create an index to the pandas series
    i = pd.Index(t)
    i_start = i.get_loc(a)
    i_end = i.get_loc(b)
    t = t[i_start:i_end]
    c = c[i_start:i_end]
    return t, c


def rm_frames_before(df_in, span, metric='Temperature (C)'):
    try:
        b = df_last_time(df_in)
        a = offset_time_mm(b, -1 * span_dict[span][2])

        # safety check
        s = df_first_time(df_in)
        if a < s:
            a = s

        return _slice_w_idx(df_in, a, b, metric)
    except (KeyError, Exception):
        return None, None


# t is time series, d data series
def slice_n_average(t, d, span):
    # prepare time jumps forward
    n_slices = span_dict[span][0]
    step = span_dict[span][1]
    i = pd.Index(t)

    # build averaged output lists
    x = []
    y = []
    start = t.values[0]
    end = offset_time_mm(start, step)
    for _ in range(n_slices):
        try:
            i_start = i.get_loc(start)
            i_end = i.get_loc(end)
            y.append(np.nanmean(d.values[i_start:i_end]))
        except (KeyError, AttributeError):
            y.append(np.nan)
        finally:
            x.append(str(start))
            start = end
            end = offset_time_mm(start, step)

    return x, y


def format_time_labels(t, span):
    lb = []
    for each_t in t:
        lb.append(iso8601.parse_date(each_t).strftime(span_dict[span][3]))
    return lb


def format_time_ticks(t, span):
    return t[::(span_dict[span][4])]


def format_title(t, span):
    last_time = iso8601.parse_date(t[-1])
    title_dict = {
        'h': 'last hour: {}'.format(last_time.strftime('%b. %d, %Y')),
        'd': 'last day: {}'.format(last_time.strftime('%b. %d, %Y')),
        'w': 'last week: {}'.format(last_time.strftime('%b. %Y')),
        'm': 'last month: {}'.format(last_time.strftime('%b. %Y')),
        'y': 'last year'
    }
    return title_dict[span]
