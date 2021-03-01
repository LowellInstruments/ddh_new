import time
from datetime import datetime
import fiona
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom
from shapely.prepared import prep
from ddh.settings import ctx
from mat.gps_quectel import get_one_gps_rmc_info


def gps_get_one_lat_lon_dt(timeout=3):
    """ gets one dummy or real GPS measurement """
    if ctx.dummy_gps:
        time.sleep(timeout / 3)
        dt = datetime.now()
        lat = '{:+.6f}'.format(12.34567866666666)
        lon = '{:+.6f}'.format(-77.777777666666667)
        return lat, lon, dt

    return get_one_gps_rmc_info()


def gps_in_land(lat, lon):
    """ tells if a GPS position is in-land """

    if ctx.dummy_gps:
        test_water = ('0', '0')
        test_land_madrid = ('40.416800', '-3.703800')
        # set the dummy you wanna test
        lat, lon = test_land_madrid

    geoms = fiona.open(shpreader.natural_earth(
        resolution='50m',
        category='physical',
        name='land'))
    polygons = [sgeom.shape(geom['geometry']) for geom in geoms]
    land_geom = sgeom.MultiPolygon(polygons)
    land = prep(land_geom)
    # lon first
    return land.contains(sgeom.Point(float(lon), float(lat)))
