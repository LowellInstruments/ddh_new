import os
import shelve
import time
from datetime import datetime
import fiona
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom
from shapely.prepared import prep
from ddh.settings import ctx
from mat.gps_quectel import gps_get_rmc_data
from mat.utils import linux_is_rpi


# be safe, set path as './' == DDH app root folder
BACKUP_GPS_SL = './.gps_cache.sl'
CACHED_GPS_VALID_TIME = 90


def utils_gps_cache_set(d):
    # d: (<lat>, <lon>, <gps_time>)
    with shelve.open(BACKUP_GPS_SL) as sh:
        till = time.perf_counter() + CACHED_GPS_VALID_TIME
        sh['last'] = (d, till)
        # print('dbg: GPS cache set till {}'.format(till))


def utils_gps_cache_get():
    try:
        with shelve.open(BACKUP_GPS_SL) as sh:
            # data: ((<lat>, <lon>, <gps_time>), till)
            data, till = sh['last']
            # check cache is not expired
            if time.perf_counter() > till:
                # print('dbg: GPS cache expired')
                return
        # print('dbg: GPS cache valid {}'.format(data))
        return data
    except (KeyError, Exception) as ex:
        # for example, at first ever
        # print('dbg: GPS cache get exception {}'.format(ex))
        return


def utils_gps_cache_is_there_any():
    return utils_gps_cache_get()


def utils_gps_cache_clear():
    if os.path.exists(BACKUP_GPS_SL):
        # print('dbg: removing {}'.format(BACKUP_GPS_SL))
        os.remove(BACKUP_GPS_SL)


def utils_gps_get_one_lat_lon_dt(timeout=3, sig=None):
    """
    returns (lat, lon, dt object) or None
    for a dummy or real GPS measurement
    """

    # debug hook, returns None
    if ctx.dbg_hook_make_gps_to_fail:
        # print('DBG: returning GPS None forced')
        return

    # debug hook, returns our custom GPS frame
    t = timeout
    if ctx.dbg_hook_make_gps_give_fake_measurement:
        if sig:
            sig.debug.emit('GPS: dbg_hook_gps_fake_measurement')

        # remember: for GPS use .utcnow(), not .now()
        time.sleep(5)
        dt = datetime.utcnow()
        lat = '{:+.6f}'.format(12.34567866666666)
        lon = '{:+.6f}'.format(-144.777777666666667)
        # you can also 'return None' to simulate an error
        return lat, lon, dt

    # no fake measurement, let's see what we are
    if not linux_is_rpi():
        # sig.debug.emit('GPS: nope for desktop / laptop')
        return

    # get one measurement None / (lat, lon, gps_time)
    d = gps_get_rmc_data(timeout=t)

    # cache in case is a good one
    if d:
        utils_gps_cache_set(d)
    return d


def utils_gps_in_land(lat, lon):
    """ tells if a GPS position is in-land """

    geoms = fiona.open(shpreader.natural_earth(
        resolution='50m',
        category='physical',
        name='land'))
    polygons = [sgeom.shape(geom['geometry']) for geom in geoms]
    land_geom = sgeom.MultiPolygon(polygons)
    land = prep(land_geom)
    # lon first
    return land.contains(sgeom.Point(float(lon), float(lat)))
