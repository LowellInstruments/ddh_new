import datetime
from tzlocal import get_localzone
from threads.utils import linux_is_net_ok, get_ntp_time, linux_set_datetime
from threads.utils_gps_internal import gps_get_one_lat_lon_dt


def time_via(w):
    via = 'local'
    if _time_sync_gps():
        via = 'GPS'
    elif _time_sync_net():
        via = 'NTP'
    w.sig_tim.status.emit('TIM: sync date via {}'.format(via))
    w.sig_tim.via.emit(via)
    return via


def _time_sync_net():
    if not linux_is_net_ok():
        return

    # 1598537165 = GMT August 27, 2020 06:05 PM
    secs = get_ntp_time()
    if secs and secs > 1598537165:
        dt = datetime.datetime.fromtimestamp(secs)
        t = dt.strftime("%d %b %Y %H:%M:%S")
        return linux_set_datetime(t)


def _time_sync_gps():
    # update only GPS time, don't care lat, lon
    _, _, gps_time = gps_get_one_lat_lon_dt()

    # this is my timezone, apply it to UTC-based datetime from GPS frame
    tz_utc = datetime.timezone.utc
    tz_me = get_localzone()
    my_dt = gps_time.replace(tzinfo=tz_utc).astimezone(tz=tz_me)

    # apply time to the box
    t = str(my_dt)[:-6]
    linux_set_datetime(t)
    return True



if __name__ == '__main__':
    _time_sync_gps()