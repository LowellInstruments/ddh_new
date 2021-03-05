import time
from datetime import datetime
import fiona
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom
from shapely.prepared import prep
from ddh.settings import ctx
from mat.gps_quectel import gps_get_rmc_frame


def utils_gps_get_one_lat_lon_dt(timeout=3):
    """
    returns (lat, lon, dt object) or None
    from a dummy or real GPS measurement
    """

    if ctx.dummy_gps:
        time.sleep(timeout / 3)
        dt = datetime.now()
        # dummy gps 1 (random)
        lat = '{:+.6f}'.format(12.34567866666666)
        lon = '{:+.6f}'.format(-77.777777666666667)
        # dummy gps 2 (Bermuda sea)
        lat = '{:+.6f}'.format(32.44826992858049)
        lon = '{:+.6f}'.format(-64.78203306587088)
        # you can also 'return None' to simulate an error
        return lat, lon, dt

    return gps_get_rmc_frame()


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
