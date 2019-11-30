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


def linux_have_internet_connection():
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


# be sure we are up-to-date with downloaded logger folders
def update_dl_folder_list():
    d = 'dl_files'
    if os.path.isdir(d):
        l = [f.path for f in os.scandir(d) if f.is_dir()]
        return l
    else:
        os.makedirs(d, exist_ok=True)


def detect_raspberry():
    node_name = os.uname()[1]
    if node_name.endswith('raspberrypi') or node_name.startswith('rpi'):
        return True
    return False


def json_check_config_file():
    import json
    try:
        with open('ddh.json') as f:
            cfg = json.load(f)
            assert len(cfg['metrics']) <= 2
    except (FileNotFoundError, TypeError, json.decoder.JSONDecodeError):
        console_log.error('SYS: error reading ddh.json config file')
        return False
    return True


def json_get_ship_name():
    import json
    try:
        with open('ddh.json') as f:
            ddh_cfg_string = json.load(f)
            return ddh_cfg_string['ship_info']['name']
    except TypeError:
        return 'Unnamed ship'


def json_get_mac_filter():
    import json
    try:
        with open('ddh.json') as f:
            ddh_cfg_string = json.load(f)
            return [x.lower() for x in ddh_cfg_string['db_logger_macs'].keys()]
    except TypeError:
        return 'Unnamed ship'


def json_get_metrics():
    import json
    with open('ddh.json') as f:
        ddh_cfg_string = json.load(f)
        return ddh_cfg_string['metrics']


def mac_from_folder(d):
    try:
        return d.split('/')[1].replace('-', ':')
    except (ValueError, Exception):
        return None


def lid_files_to_csv(folder):
    if not os.path.exists(folder):
        return None

    parameters = default_parameters()
    for f in list_files_by_extension_in_dir(folder, 'lid'):
        bn = f.split('.')[0]
        if not glob.glob(bn + '*.csv'):
            # converting takes about 1.5 seconds per file
            DataConverter(bn + '.lid', parameters).convert()


def _metric_to_csv_file_suffix(metric):
    metric_dict = {
        'DOS': '_DissolvedOxygen',
        'DOP': '_DissolvedOxygen',
        'DOT': '_DissolvedOxygen',
        'T': '_Temperature',
        'P': '_Pressure',
    }
    return metric_dict[metric]


def csv_to_data_frames(folder, metric):
    try:
        # get all csv rows, concat them, ensure ordered
        suffix = _metric_to_csv_file_suffix(metric)
        mask = folder + '/*' + suffix + '.csv'
        all_csv_rows = [pd.read_csv(f) for f in glob.glob(mask)]
        p_df = pd.concat(all_csv_rows, ignore_index=True)
        p_df = p_df.sort_values(by=['ISO 8601 Time'])
        return p_df
    except (IOError, Exception) as e:
        print(e)
        return None


def json_mac_dns(logger_mac):
    import json
    name = 'unnamed_logger'
    try:
        with open('ddh.json') as f:
            ddh_cfg_string = json.load(f)
            name = ddh_cfg_string['db_logger_macs'][logger_mac]
    except (FileNotFoundError, TypeError, KeyError):
        pass
    return name


# t is a string
def offset_time_mm(t, mm):
    a = datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.000')
    a += datetime.timedelta(minutes=mm)
    return a.strftime('%Y-%m-%dT%H:%M:%S.000')


# a and b are time strings
# def _slice_w_idx(df_in, a, b, column_name):
#     # compute() returns a panda series
#     t = df_in['ISO 8601 Time'].compute()
#     c = df_in[column_name].compute()
#     # create an index to the pandas series
#     i = pd.Index(t)
#     i_start = i.get_loc(a)
#     print(i_start)
#     # i_end = i.get_loc(b)
#     # print('4')
#     # t = t[i_start:i_end]
#     # c = c[i_start:i_end]
#     w = t[t == object(a)]
#     print(w)
#     return t, c


def _slice_w_idx(p_df, a, b, column_name):
    t = p_df['ISO 8601 Time']
    c = p_df[column_name]
    print('1')
    i_start = t[t == a].keys()[0]
    i_end = t[t == b].keys()[0]
    print(i_start)
    print(i_end)
    t = t[i_start:i_end]
    c = c[i_start:i_end]
    return t,c


def del_frames_before(p_df, span, column_name):
    try:
        # get ending time and starting time
        b = p_df['ISO 8601 Time'].values[-1]
        a = offset_time_mm(b, -1 * span_dict[span][2])

        # safety check
        s = p_df['ISO 8601 Time'].values[0]
        if a < s:
            a = s
        return _slice_w_idx(p_df, a, b, column_name)
    except (KeyError, Exception) as e:
        print('PUTA')
        print(e)
        return None, None


# t is time series, d data series
def slice_n_average(t, d, span):
    # prepare time jumps forward
    n_slices = span_dict[span][0]
    step = span_dict[span][1]
    if t is None:
        return None, None
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


def plot_format_time_labels(t, span):
    lb = []
    for each_t in t:
        lb.append(iso8601.parse_date(each_t).strftime(span_dict[span][3]))
    return lb


def plot_format_time_ticks(t, span):
    return t[::(span_dict[span][4])]


def plot_format_title(t, span):
    last_time = iso8601.parse_date(t[-1])
    title_dict = {
        'h': 'last hour: {}'.format(last_time.strftime('%b. %d, %Y')),
        'd': 'last day: {}'.format(last_time.strftime('%b. %d, %Y')),
        'w': 'last week: {}'.format(last_time.strftime('%b. %Y')),
        'm': 'last month: {}'.format(last_time.strftime('%b. %Y')),
        'y': 'last year'
    }
    return title_dict[span]


def plot_line_color(column_name):
    color_dict = {
        'Temperature (C)':  'tab:red',
        'Pressure (psi)':   'tab:blue',
        'Dissolved Oxygen (mg/l)': 'black',
        'Dissolved Oxygen (%)': 'black',
        'DO Temperature (C)': 'tab:red',
    }
    return color_dict[column_name]


def metric_to_column_name(metric):
    metric_dict = {
        'T':    'Temperature (C)',
        'P':    'Pressure (psi)',
        'DOS':  'Dissolved Oxygen (mg/l)',
        'DOP':  'Dissolved Oxygen (%)',
        'DOT':  'DO Temperature (C)',

    }
    return metric_dict[metric]
