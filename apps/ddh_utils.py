import datetime
import http.client
import subprocess
import shlex
import socket
import os
import glob
import bisect
import iso8601
from logzero import logger as console_log
from mat.data_converter import DataConverter, default_parameters
import pandas as pd
import numpy as np
import json


def linux_set_time_from_gps(when):
    # timedatectl: UNIX command to stop systemd-timesyncd.service
    time_string = datetime.datetime(*when).isoformat()
    subprocess.call(shlex.split('sudo timedatectl set-ntp false'))
    subprocess.call(shlex.split("sudo date -s '%s'" % time_string))

    # raspberry has no RTC so avoid the following
    # subprocess.call(shlex.split('sudo hwclock -w'))


def linux_detect_raspberry():
    node_name = os.uname()[1]
    if node_name.endswith('raspberrypi') or node_name.startswith('rpi'):
        return True
    return False


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
def linux_ls_by_ext(dir_name, extension):
    if not dir_name:
        return []
    if os.path.isdir(dir_name):
        wildcard = dir_name + '/**/*.' + extension
        return glob.glob(wildcard, recursive=True)


# be sure we up-to-date w/ downloaded logger folders
def update_dl_folder_list():
    d = 'dl_files'
    if os.path.isdir(d):
        f_l = [f.path for f in os.scandir(d) if f.is_dir()]
        return f_l
    else:
        os.makedirs(d, exist_ok=True)


def json_check_config_file():
    try:
        with open('ddh.json') as f:
            cfg = json.load(f)
            assert len(cfg['metrics']) <= 2
    except (FileNotFoundError, TypeError, json.decoder.JSONDecodeError):
        console_log.error('SYS: error reading ddh.json config file')
        return False
    return True


def json_get_ship_name():
    try:
        with open('ddh.json') as f:
            cfg = json.load(f)
            return cfg['ship_info']['name']
    except TypeError:
        return 'Unnamed ship'


def json_get_forget_time_secs():
    try:
        with open('ddh.json') as f:
            cfg = json.load(f)
            return int(cfg['forget_time'])
    except TypeError:
        return 'Unnamed ship'


def json_get_mac_filter():
    try:
        with open('ddh.json') as f:
            cfg = json.load(f)
            return [x.lower() for x in cfg['db_logger_macs'].keys()]
    except TypeError:
        return 'Unnamed ship'


def json_get_metrics():
    with open('ddh.json') as f:
        cfg = json.load(f)
        return cfg['metrics']


def json_get_span_dict():
    with open('ddh.json') as f:
        cfg = json.load(f)
        return cfg['span_dict']


def json_mac_dns(logger_mac):
    name = 'unnamed_logger'
    try:
        with open('ddh.json') as f:
            cfg = json.load(f)
            name = cfg['db_logger_macs'][logger_mac]
    except (FileNotFoundError, TypeError, KeyError):
        pass
    return name


def mac_from_folder(d):
    try:
        return d.split('/')[1].replace('-', ':')
    except (ValueError, Exception):
        return None


def lid_to_csv(folder):
    if not os.path.exists(folder):
        return None

    parameters = default_parameters()
    for f in linux_ls_by_ext(folder, 'lid'):
        bn = f.split('.')[0]

        # check if csv file exists
        if not glob.glob(bn + '*.csv'):
            # converting takes about 1.5 seconds per file
            DataConverter(bn + '.lid', parameters).convert()


def _metric_to_csv_suffix(metric):
    metric_dict = {
        'DOS': '_DissolvedOxygen',
        'DOP': '_DissolvedOxygen',
        'DOT': '_DissolvedOxygen',
        'T': '_Temperature',
        'P': '_Pressure',
    }
    return metric_dict[metric]


def csv_to_df(folder, metric):
    try:
        # get all csv rows, concat them, ensure ordered
        suffix = _metric_to_csv_suffix(metric)
        mask = folder + '/*' + suffix + '.csv'
        all_csv_rows = [pd.read_csv(f) for f in glob.glob(mask)]
        df = pd.concat(all_csv_rows, ignore_index=True)
        return df.sort_values(by=['ISO 8601 Time'])
    except (IOError, Exception):
        # e.g. nothing to concatenate
        return None


# t is a string
def off_mm(t, mm):
    a = datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.000')
    a += datetime.timedelta(minutes=mm)
    return a.strftime('%Y-%m-%dT%H:%M:%S.000')


def rm_df_before(df, span, c):
    try:
        # get ending (e) time and adjusted (a) starting (s) time
        span_dict = json_get_span_dict()
        e = df['ISO 8601 Time'].values[-1]
        s = off_mm(e, -1 * span_dict[span][2])
        a = df['ISO 8601 Time'].values[0]
        if s < a:
            s = a

        # slice data frame and return two series
        df = df[df['ISO 8601 Time'] >= s]
        df = df[df['ISO 8601 Time'] <= e]
        return df['ISO 8601 Time'], df[c]
    except (KeyError, Exception):
        # print(exc)
        return None, None


# t is time series, d data series
def slice_n_avg(t, d, span):
    span_dict = json_get_span_dict()
    n_slices = span_dict[span][0]
    step_mm = span_dict[span][1]
    if t is None:
        return None, None

    # build averaged output lists
    x = []
    y = []
    s = t.values[0]
    e = off_mm(s, step_mm)
    i = list(t.values)

    # t.values: np.array, t: np.series, t.values[x]: str
    for _ in range(n_slices):
        try:
            # y axis: contains data
            i_s = bisect.bisect_left(i, s)
            i_e = bisect.bisect_left(i, e)
            sl = d.values[i_s:i_e]
            v = np.nanmean(sl)
            y.append(v) if sl.any() else y.append(np.nan)
        except (KeyError, Exception) as e:
            print('** {}'.format(e))
        finally:
            # x axis: contains timestamps
            x.append(s)
            s = e
            e = off_mm(s, step_mm)
    return x, y


def plot_format_time_labels(t, span):
    lb = []
    for each in t:
        span_dict = json_get_span_dict()
        fmt_t = iso8601.parse_date(each).strftime(span_dict[span][3])
        lb.append(fmt_t)
    return lb


def plot_format_time_ticks(t, span):
    span_dict = json_get_span_dict()
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
        'Pressure (dbar)':   'tab:blue',
        'Dissolved Oxygen (mg/l)': 'black',
        'Dissolved Oxygen (%)': 'black',
        'DO Temperature (C)': 'tab:red',
    }
    return color_dict[column_name]


def plot_metric_to_column_name(metric):
    metric_dict = {
        'T':    'Temperature (C)',
        'P':    'Pressure (dbar)',
        'DOS':  'Dissolved Oxygen (mg/l)',
        'DOP':  'Dissolved Oxygen (%)',
        'DOT':  'DO Temperature (C)',

    }
    return metric_dict[metric]


def plot_metric_to_label_name(metric):
    metric_dict = {
        'T':    'Temperature (C)',
        'P':    'Depth (m)',
        'DOS':  'Dissolved Oxygen (mg/l)',
        'DOP':  'Dissolved Oxygen (%)',
        'DOT':  'DO Temperature (C)',

    }
    return metric_dict[metric]
