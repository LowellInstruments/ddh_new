import datetime
from threads.utils import linux_is_net_ok, get_ntp_time, linux_set_datetime
from threads.utils_gps_internal import get_gps_lat_lon_more


def emit_time_status(sig, s):
    if sig:
        sig.status.emit(s)


def emit_time_gui_update(sig, b):
    if sig:
        sig.update.emit(b)


def time_sync_net():
    if linux_is_net_ok():
        s = 'CLK: NTP-RAW sync'
        secs = get_ntp_time()
        # 1598537165 = 20/08/27 10:06:05 GMT-04:00
        if secs and secs > 1598537165:
            dt = datetime.datetime.fromtimestamp(secs)
            t = dt.strftime("%d %b %Y %H:%M:%S")
            if linux_set_datetime(t):
                return True

def time_sync_gps():
    data = get_gps_lat_lon_more()
    # todo: redo this below
    return True

#     # GPS datetime object, UTC, no timezone info
#     g_dt = f.timestamp
#
#     # this is my timezone
#     tz_utc = timezone.utc
#     tz_me = get_localzone()
#
#     # new datetime = gps datetime + apply timezone
#     my_dt = g_dt.replace(tzinfo=tz_utc).astimezone(tz=tz_me)
#
#     # between v3.6 and v3.7, let's do ours
#     t = str(my_dt)[:-6]
#     linux_set_datetime(t)
