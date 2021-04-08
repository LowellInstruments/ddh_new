import datetime
from tzlocal import get_localzone

from ddh.settings import ctx
from ddh.threads.utils import linux_is_net_ok, get_ntp_time, linux_set_datetime
from ddh.threads.utils_gps_quectel import utils_gps_get_one_lat_lon_dt


def utils_time_update_datetime_source(w):

    # preferred NTP > GPS > local
    via = 'local'
    if _time_sync_net():
        via = 'NTP'
    else:
        if _time_sync_gps():
            via = 'GPS'
    w.sig_tim.status.emit('TIM: sync date via {}'.format(via))
    w.sig_tim.via.emit(via)
    return via


def _time_sync_net():

    # debug hook, forces NTP clock sync to fail
    if ctx.dbg_hook_make_ntp_to_fail:
        print('DBG: ctx.dbg_hook_make_ntp_to_fail == 1')
        return

    # we cannot NTP without internet access
    if not linux_is_net_ok():
        return

    # 1598537165 = GMT August 27, 2020 06:05 PM
    secs = get_ntp_time()
    if secs and secs > 1598537165:
        dt = datetime.datetime.fromtimestamp(secs)
        t = dt.strftime("%d %b %Y %H:%M:%S")
        return linux_set_datetime(t)


def _time_sync_gps():

    # gps_time is datetime in UTC, NOT a string, ignore lat, lon
    g = utils_gps_get_one_lat_lon_dt()
    _, _, dt_gps = g if g else (None, ) * 3
    if not dt_gps:
        return False

    # get my timezone, format the UTC GPS datetime object as it
    z_my = get_localzone()
    z_utc = datetime.timezone.utc
    dt_my = dt_gps.replace(tzinfo=z_utc).astimezone(tz=z_my)

    # stringify and apply time to the box
    t = str(dt_my)[:-6]
    linux_set_datetime(t)
    return True


if __name__ == '__main__':

    _time_sync_gps()
