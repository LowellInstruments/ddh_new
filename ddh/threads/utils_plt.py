import bisect
import datetime
import glob
import warnings

import iso8601
import pandas as pd

from ddh.settings import ctx
from ddh.db.db_plt import DBPlt
from ddh.threads.utils import (
    get_mac_from_folder_path,
    lid_to_csv, emit_status, emit_error, emit_debug)
import numpy as np


def emit_start(sig):
    if sig:
        sig.start.emit()


def emit_result(sig, rv, s):
    if sig:
        sig.result.emit(rv, s)


def _metric_to_csv_suffix(metric):
    metric_dict = {
        'DOS': '_DissolvedOxygen',
        'DOP': '_DissolvedOxygen',
        'DOT': '_DissolvedOxygen',
        'T': '_Temperature',
        'P': '_Pressure',
    }
    return metric_dict[metric]


def _csv_to_df(folder, metric):
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


def _off_mm(t: str, mm):
    """ calculates forward in time """
    a = datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.000')
    a += datetime.timedelta(minutes=mm)
    return a.strftime('%Y-%m-%dT%H:%M:%S.000')


# prune data frame and return time, data series
def _rm_df_before(df, c, ts):
    try:
        # get ending (e) time and adjusted (a) starting (s) time
        e = df['ISO 8601 Time'].values[-1]
        s = _off_mm(e, -1 * ts[2])
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


def _fmt_x_labels(t, span, sd):
    lb = []
    for each in t:
        fmt_t = iso8601.parse_date(each).strftime(sd[span][3])
        lb.append(fmt_t)
    return lb


def _fmt_x_ticks(t, span, sd):
    return t[::(sd[span][4])]


def _fmt_title(t, span):
    last_time = iso8601.parse_date(t[-1])
    title_dict = {
        'h': 'last hour: {}'.format(last_time.strftime('%b. %d, %Y')),
        'd': 'last day: {}'.format(last_time.strftime('%b. %d, %Y')),
        'w': 'last week: {}'.format(last_time.strftime('%b. %Y')),
        'm': 'last month: {}'.format(last_time.strftime('%b. %Y')),
        'y': 'last year'
    }
    return title_dict[span]


def _line_color(column_name):
    color_dict = {
        'Temperature (C)':  'tab:red',
        'Pressure (dbar)':   'tab:blue',
        'Dissolved Oxygen (mg/l)': 'black',
        'Dissolved Oxygen (%)': 'black',
        'DO Temperature (C)': 'tab:red',
    }
    return color_dict[column_name]


def _metric_to_col_name(metric):
    metric_dict = {
        'T':    'Temperature (C)',
        'P':    'Pressure (dbar)',
        'DOS':  'Dissolved Oxygen (mg/l)',
        'DOP':  'Dissolved Oxygen (%)',
        'DOT':  'DO Temperature (C)',

    }
    return metric_dict[metric]


def _metric_to_legend_name(metric):
    metric_dict = {
        'T':    'Temperature (C)',
        'P':    'Depth (m)',
        'DOS':  'Dissolved Oxygen (mg/l)',
        'DOP':  'Dissolved Oxygen (%)',
        'DOT':  'DO Temperature (C)',

    }
    return metric_dict[metric]


# t, d: time, data series / ts: [4, 15, 60, '%H:%M', 1]
def _slice_n_avg(t, d, ts, sig):
    if t is None:
        return None, None

    # grab number of slices and duration of each
    n_slices, mm_each_slice = ts[0], ts[1]
    n_slices_nan = 0

    # i -> all times, x -> timestamps, y -> data
    x, y = [], []
    i = list(t.values)

    # calculate first slice
    s = i[0]
    e = _off_mm(s, mm_each_slice)
    for _ in range(n_slices):
        try:
            # i_x: indexes, NOT minutes, or hours, or whatever
            i_s = bisect.bisect_left(i, s)
            i_e = bisect.bisect_left(i, e)
            sl = d.values[i_s:i_e]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                v = np.nanmean(sl)

            # no bad slices treatment: y -> data
            y.append(v)

            # bad slices treatment: y -> data only after checked
            # good_mean_for_this_slice = sl.any()
            # if good_mean_for_this_slice:
            #     y.append(v)
            # else:
            #     # not so good one, p.e. all 0
            #     # emit_debug(sig, 'PLT: bad slice')
            #     n_slices_nan += 1
            #     y.append(np.nan)

        except (KeyError, Exception) as e:
            print('** {}'.format(e))

        finally:
            # x axis: timestamps, calculate new slice
            x.append(s)
            s = e
            e = _off_mm(s, mm_each_slice)

    # bad slices treatment: summary
    # num_good_slices = len(x) - n_slices_nan
    # if num_good_slices < 2:
    #     e = 'PLT: process -> argh, good slices {} < 2'
    #    emit_debug(sig, e.format(num_good_slices))

    return x, y


def _cache_or_process(sig, folder, ts, metric, sd):

    # metadata
    emit_status(sig, 'PLT: process -> {}'.format(metric))
    c = _metric_to_col_name(metric)
    mac = get_mac_from_folder_path(folder)

    # convert from LID to CSV format
    suffix = _metric_to_csv_suffix(metric)
    lid_to_csv(folder, suffix, sig)

    # load + prune CSV data within last 'ts'
    df = _csv_to_df(folder, metric)
    x, y = _rm_df_before(df, c, sd[ts])
    s, e = x.values[0], x.values[-1]

    # check processed CSV data exists in cache
    p = ctx.db_plt
    db = DBPlt(p)
    if db.does_record_exist(mac, s, e, ts, c):
        # cached! retrieve it from database
        emit_status(sig, 'PLT: process cache hit')
        r_id = db.get_record_id(mac, s, e, ts, c)
        t = db.get_record_times(r_id)
        y_avg = db.get_record_values(r_id)
        return t, y_avg

    # not cached! process it and cache it
    t, y_avg = _slice_n_avg(x, y, sd[ts], sig)
    db.add_record(mac, s, e, ts, c, t, y_avg)
    return t, y_avg


# folder, matplotlib axes, time_span, metrics, span_dict, logger_name
def plot(sig, fol, ax, ts, metric_pair, sd, lg):
    m_p = metric_pair
    f = fol.split('/')[-1]
    c0 = _metric_to_col_name(m_p[0])
    c1 = _metric_to_col_name(m_p[1])
    l0 = _metric_to_legend_name(m_p[0])
    l1 = _metric_to_legend_name(m_p[1])
    clr0 = _line_color(c0)
    clr1 = _line_color(c1)

    # metric 1 of 2, required, query database
    try:
        t, y0 = _cache_or_process(sig, fol, ts, m_p[0], sd)
    except (AttributeError, Exception) as ex:
        # e.g. when no values at all, None.values
        e = 'PLT: process -> error {}({}) for {}'
        emit_error(sig, e.format(m_p[0], ts, f))
        return False

    # metric 2 of 2, not always required, query database
    try:
        _, y1 = _cache_or_process(sig, fol, ts, m_p[1], sd)
    except (AttributeError, Exception):
        y1 = None
        e1 = 'process -> error {}({}) for {}'
        emit_error(sig, e1.format(m_p[1], ts, f))

    # line plot needs at least 2 points
    good_dots = np.count_nonzero(~np.isnan(y0))
    if good_dots < 2:
        e = 'PLT: process -> few {}({}) dots for {}'.format(m_p, ts, f)
        emit_error(sig, e)
        return False

    # metric 1 of 2, get axis
    ax.figure.clf()
    ax.figure.tight_layout()
    ax0 = ax.figure.add_subplot(111)

    # metric 1 of 2, hack for Fahrenheits T display
    if y0 and l0 == 'DO Temperature (C)' and ctx.plt_units == 'F':
        l0 = 'DO Temperature (F)'
        y0 = [((i * 9 / 5) + 32) for i in y1]

    # metric 1 of 2, hack for P / depth display
    if y0 and l0 == 'Depth (m)':
        ax0.invert_yaxis()

    # metric 1 of 2, plot
    tit = _fmt_title(t, ts)
    sym = '{} '.format('\u2014')
    ax0.set_ylabel(sym + l0, fontsize='large', fontweight='bold', color=clr0)
    ax0.tick_params(axis='y', labelcolor=clr0)
    ax0.plot(t, y0, label=l0, color=clr0)
    ax0.set_xlabel('time', fontsize='large', fontweight='bold')
    ax0.set_title('Logger ' + lg + ', ' + tit, fontsize='x-large')
    lbs = _fmt_x_ticks(t, ts, sd)

    # metric 2 of 2, not always present, get axis
    if y1:
        ax1 = ax0.twinx()

        # metric 2 of 2, hack for Fahrenheits T display
        if y1 and l1 == 'DO Temperature (C)' and ctx.plt_units == 'F':
            l1 = 'DO Temperature (F)'
            y1 = [((i * 9 / 5) + 32) for i in y1]

        # metric 2 of 2, hack for P / depth display
        if l1 == 'Depth (m)':
            ax1.invert_yaxis()

        # metric 2 of 2, plot
        sym = '- -  '
        ax1.set_ylabel(sym + l1, fontsize='large', fontweight='bold', color=clr1)
        ax1.tick_params(axis='y', labelcolor=clr1)
        ax1.plot(t, y1, '--', label=l1, color=clr1)
        ax1.set_xticks(lbs)

    # common labels MUST be formatted here, at the end
    # cnv.figure.legend(bbox_to_anchor=[0.9, 0.5], loc='center right')
    ax0.set_xticklabels(_fmt_x_labels(lbs, ts, sd))
    ax0.set_xticks(lbs)
    cnv = ax.figure.canvas
    cnv.draw()
    return True

