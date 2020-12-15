import datetime
from tzlocal import get_localzone
from threads.utils import linux_is_net_ok, get_ntp_time, linux_set_datetime
from threads.utils_gps_internal import get_gps_lat_lon_more


def emit_time_status(sig, s):
    if sig:
        sig.status.emit(s)


def emit_time_gui_update(sig, b):
    if sig:
        sig.update.emit(b)


def time_via(w, emit=True):
    via = 'local'
    if time_sync_gps():
        via = 'GPS'
    elif time_sync_net():
        via = 'NTP'
    w.sig_tim.status.emit('TIM: sync {}'.format(via))
    w.sig_tim.via.emit(via)
    return via


def time_sync_net():
    if linux_is_net_ok():
        secs = get_ntp_time()
        # 1598537165 = 20/08/27 10:06:05 GMT-04:00
        if secs and secs > 1598537165:
            dt = datetime.datetime.fromtimestamp(secs)
            t = dt.strftime("%d %b %Y %H:%M:%S")
            if linux_set_datetime(t):
                return True

# todo: test this, seems complete
def time_sync_gps():
    # data -> (lat, lon, dt object)
    # data = get_gps_lat_lon_more()

    # todo: remove after testing
    data = (77.28940666666666, 11.516666666666667, datetime.datetime(1994, 3, 23, 12, 35, 19))

    # this is my timezone, apply it to UTC-based datetime from GPS frame
    tz_utc = datetime.timezone.utc
    tz_me = get_localzone()
    my_dt = data[2].replace(tzinfo=tz_utc).astimezone(tz=tz_me)
    print(my_dt)

    # apply time to the box
    t = str(my_dt)[:-6]
    # linux_set_datetime(t)
    return True



if __name__ == '__main__':
    time_sync_gps()