import time
from datetime import datetime,
import serial
from mat.gps_quectel import gps_parse_rmc_frame, PORT_DATA, enable_gps_quectel_output
import fiona
import cartopy.io.shapereader as shpreader
import shapely.geometry as sgeom
from shapely.prepared import prep


def emit_gps_update_pos(sig, lat, lon):
    if sig:
        sig.update_pos.emit(lat, lon)


def emit_gps_update_time_via(sig, via):
    if sig:
        sig.update_time_via.emit(via)


def emit_gps_status(sig, s):
    if sig:
        sig.status.emit(s)


def emit_gps_error(sig, e):
    if sig:
        sig.error.emit(e)


def get_gps_data(timeout=3):
    # todo: remove when GPS attached
    time.sleep(timeout / 3)
    dt = datetime(1994, 3, 23, 12, 35, 19)
    lat = '{:.6f}'.format(77.28940666666666)
    lon = '{:.6f}'.format(11.516666666666667)
    return (lat, lon, dt)


    _till = time.perf_counter() + timeout
    enable_gps_quectel_output()
    print('GPS Quectel receiving...')
    sp = serial.Serial(PORT_DATA, baudrate=115200, timeout=0.5)

    while True:
        if time.perf_counter() > _till:
            break
        data = sp.readline()
        if '$GPRMC' in data:
            rv = gps_parse_rmc_frame(data)
            if rv:
                return rv
    return None


# todo: use this
def gps_in_land(lat, lon):
    geoms = fiona.open(
        shpreader.natural_earth(resolution='50m',
                                category='physical', name='land'))
    land_geom = sgeom.MultiPolygon([sgeom.shape(geom['geometry'])
                                    for geom in geoms])
    land = prep(land_geom)
    # lon first
    return land.contains(sgeom.Point(float(lon), float(lat)))
