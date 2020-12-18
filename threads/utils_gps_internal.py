import time
from datetime import datetime
import serial
from mat.gps_quectel import gps_parse_rmc_frame, PORT_DATA, enable_gps_quectel_output
import fiona
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom
from shapely.prepared import prep


def gps_get_one_lat_lon_dt(timeout=3):
    # todo: on production, remove when GPS attached
    time.sleep(timeout / 3)
    dt = datetime(1994, 3, 23, 12, 35, 19)
    lat = '{:.6f}'.format(77.28940666666666)
    lon = '{:.6f}'.format(11.516666666666667)
    return (lat, lon, dt)


    # uncomment on production
    # _till = time.perf_counter() + timeout
    # enable_gps_quectel_output()
    # # print('GPS Quectel receiving...')
    # sp = serial.Serial(PORT_DATA, baudrate=115200, timeout=0.5)
    #
    # while True:
    #     if time.perf_counter() > _till:
    #         break
    #     data = sp.readline()
    #     if b'$GPRMC' in data:
    #         rv = gps_parse_rmc_frame(data)
    #         if rv:
    #             return rv
    # return None


def gps_in_land(lat, lon):
    # for testing purposes
    # test_water = (0, 0)
    # test_land_madrid = (40.416800, -3.703800)
    # lat, lon = test_land_madrid


    geoms = fiona.open(shpreader.natural_earth(resolution='50m',
                                               category='physical', name='land'))
    land_geom = sgeom.MultiPolygon([sgeom.shape(geom['geometry'])
                                    for geom in geoms])
    land = prep(land_geom)
    # lon first
    return land.contains(sgeom.Point(float(lon), float(lat)))
