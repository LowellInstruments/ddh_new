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


# be safe, set this path as './' == DDH app root folder
from mat.utils import linux_is_rpi

BACKUP_GPS_SL = './.gps_cache.sl'
CACHED_GPS_VALID_TIME = 90


def utils_gps_cache_set(d):
    # d: ('12.3456', '44.444444', ...)
    t = time.perf_counter()
    with shelve.open(BACKUP_GPS_SL) as sh:
        sh['last'] = (d, t)


def utils_gps_cache_get():
    try:
        with shelve.open(BACKUP_GPS_SL) as sh:
            b = sh['last']
        # check cache is recent enough, o/w too old
        if b[1] + CACHED_GPS_VALID_TIME < time.perf_counter():
            return None
        return b[0]
    except (KeyError, Exception) as ex:
        return None


def utils_gps_cache_is_there_any():
    return utils_gps_cache_get()


def utils_gps_cache_clear():
    if os.path.exists(BACKUP_GPS_SL):
        os.remove(BACKUP_GPS_SL)


def utils_gps_get_one_lat_lon_dt(timeout=3, sig=None):
    """
    returns (lat, lon, dt object) or None
    for a dummy or real GPS measurement
    """

    # debug hook, returns our custom GPS frame
    t = timeout
    if ctx.dbg_hook_make_gps_give_fake_measurement:
        if sig:
            sig.debug.emit('GPS: dbg_hook_gps_fake_measurement')

        # remember: for GPS use .utcnow(), not .now()
        time.sleep(t / 3)
        dt = datetime.utcnow()
        # dummy gps 1 (random)
        lat = '{:+.6f}'.format(12.34567866666666)
        lon = '{:+.6f}'.format(-77.777777666666667)
        # dummy gps 2 (Bermuda sea)
        lat = '{:+.6f}'.format(32.44826992858049)
        lon = '{:+.6f}'.format(-64.78203306587088)
        # you can also 'return None' to simulate an error
        return lat, lon, dt

    # no fake measurement, let's see what we are
    if not linux_is_rpi():
        # sig.debug.emit('GPS: nope for desktop / laptop')
        return None

    # get one measurement and cache in case OK
    d = gps_get_rmc_data(timeout=t)
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
