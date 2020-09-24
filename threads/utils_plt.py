import bisect
import datetime
import glob
import iso8601
import pandas as pd

from settings import ctx
from db.db_plt import DBPlt
from threads.utils import (
    mac_from_folder,
    lid_to_csv)
import numpy as np


def emit_error(sig, e):
    if sig:
        sig.plt_error.emit(e)


def emit_status(sig, s):
    if sig:
        sig.plt_status.emit(s)


def emit_start(sig):
    if sig:
        sig.plt_start.emit()


def emit_result(sig, rv, s):
    if sig:
        sig.plt_result.emit(rv, s)


def emit_msg(sig, m):
    if sig:
        sig.plt_msg.emit(m)


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


# t is a string
def _off_mm(t, mm):
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


# t is time series, d data series
def _slice_n_avg(t, d, ts, sig):
    n_slices = ts[0]
    n_slices_nan = 0
    step_mm = ts[1]
    if t is None:
        return None, None

    # build averaged output lists
    x = []
    y = []
    s = t.values[0]
    e = _off_mm(s, step_mm)
    i = list(t.values)

    # t: np.series, t.values: np.array, t.values[x]: str
    for _ in range(n_slices):
        try:
            # y axis: contains data
            i_s = bisect.bisect_left(i, s)
            i_e = bisect.bisect_left(i, e)
            sl = d.values[i_s:i_e]
            v = np.nanmean(sl)
            if sl.any():
                # good mean for this slice
                y.append(v)
            else:
                # not so good one
                n_slices_nan += 1
                y.append(np.nan)
        except (KeyError, Exception) as e:
            print('** {}'.format(e))
        finally:
            # x axis: timestamps, update slice sides
            x.append(s)
            s = e
            e = _off_mm(s, step_mm)

    # summary
    if len(x) - n_slices_nan < 2:
        e = 'PLT: argh, good slices < 2'
        sig.plt_error.emit(e)
    return x, y


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


def _cache_or_process(sig, folder, ts, metric, sd):
    # metadata
    c = _metric_to_col_name(metric)
    mac = mac_from_folder(folder)

    # load + prune data within last 'ts'
    suffix = _metric_to_csv_suffix(metric)
    lid_to_csv(folder, suffix)
    df = _csv_to_df(folder, metric)
    x, y = _rm_df_before(df, c, sd[ts])
    s, e = x.values[0], x.values[-1]

    # DBPlt cache check
    p = ctx.db_plt
    db = DBPlt(p)
    if db.does_record_exist(mac, s, e, ts, c):
        # data from cached database
        emit_status(sig, 'PLT: cache hit')
        r_id = db.get_record_id(mac, s, e, ts, c)
        t = db.get_record_times(r_id)
        y_avg = db.get_record_values(r_id)
        return t, y_avg

    # not cached, process data and cache
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
    s = 'PLT: plotting {}({}) for {}'.format(m_p, ts, f)
    emit_status(sig, s)

    # query database for 1st metric in pair, important one
    try:
        t, y0 = _cache_or_process(sig, fol, ts, m_p[0], sd)
    except (AttributeError, Exception) as ex:
        # e.g. when no values at all, None.values
        e = 'PLT: error _cache_or_process {}({}) for {}'
        emit_error(sig, e.format(m_p[0], ts, f))
        # print(ex)
        return False

    # query DB for 2nd metric in pair, not critical
    try:
        _, y1 = _cache_or_process(sig, fol, ts, m_p[1], sd)
    except (AttributeError, Exception):
        e1 = 'PLT: no {}({}) for {}'.format(m_p[1], ts, f)
        y1 = None
        emit_error(sig, e1)

    # a line plot needs at least 2 points
    good_dots = np.count_nonzero(~np.isnan(y0))
    if good_dots < 2:
        e = 'PLT: few {}({}) dots for {}'.format(m_p, ts, f)
        emit_error(sig, e)
        m = 'few data to plot 1 {} of {}'.format(ts, f)
        emit_msg(sig, m)
        return False

    # prepare for plotting 1st data y0
    ax.figure.clf()
    ax.figure.tight_layout()
    tit = _fmt_title(t, ts)
    ax1 = ax.figure.add_subplot(111)
    sym = '{} '.format('\u2014')
    ax1.set_ylabel(sym + l0, fontsize='large', fontweight='bold', color=clr0)
    ax1.tick_params(axis='y', labelcolor=clr0)

    # hack for pressure / depth display
    if l0 == 'Depth (m)':
        ax1.invert_yaxis()

    ax1.plot(t, y0, label=l0, color=clr0)
    ax1.set_xlabel('time', fontsize='large', fontweight='bold')
    ax1.set_title('Logger ' + lg + ', ' + tit, fontsize='x-large')
    lbs = _fmt_x_ticks(t, ts, sd)

    # prepare for plotting 2nd data, y1, if any
    if y1:
        sym = '- -  '
        ax2 = ax1.twinx()
        ax2.set_ylabel(sym + l1, fontsize='large', fontweight='bold', color=clr1)
        ax2.tick_params(axis='y', labelcolor=clr1)

        # hack for pressure / depth display
        if l1 == 'Depth (m)':
            ax2.invert_yaxis()

        ax2.plot(t, y1, '--', label=l1, color=clr1)
        ax2.set_xticks(lbs)

    # common labels MUST be formatted here, at the end
    # cnv.figure.legend(bbox_to_anchor=[0.9, 0.5], loc='center right')
    ax1.set_xticklabels(_fmt_x_labels(lbs, ts, sd))
    ax1.set_xticks(lbs)
    cnv = ax.figure.canvas
    cnv.draw()
    return True

