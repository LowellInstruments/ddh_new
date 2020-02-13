import bluepy.btle as ble
import time
import os
import datetime
from mat.logger_controller import (
    STATUS_CMD,
    RWS_CMD,
    SWS_CMD
)
from mat.logger_controller_ble import (
    LoggerControllerBLE as LoggerControllerBLE
)
from apps.ddh_gps import DeckDataHubGPS
from apps.ddh_utils import json_get_forget_time_secs


class DeckDataHubBLE:

    WANTED_FILE_TYPES = '.lid'
    BLK_LIST = {}
    FORGET_S = json_get_forget_time_secs()
    IGNORE_S = 30
    LOGGERS_TO_QUERY = []
    dl_flag = False

    @staticmethod
    def ble_toggle_dl():
        ddh_ble.dl_flag = not ddh_ble.dl_flag
        return ddh_ble.dl_flag

    @staticmethod
    def _ble_ignore_for(mac, seconds):
        ddh_ble.BLK_LIST[mac] = time.time() + seconds

    @staticmethod
    def ble_loop(signals, ble_mac_filter):
        while 1:
            if ddh_ble._ble_scan_loggers(signals, ble_mac_filter):
                ddh_ble._ble_dl_loggers(signals)
            time.sleep(2)

    @staticmethod
    def _ble_scan_loggers(signals, ble_mac_filter):
        signals.ble_scan_start.emit()
        try:
            scanner = ble.Scanner()
            list_all_ble = scanner.scan(5.0)
        except ble.BTLEException:
            signals.error.emit('BLE: error scanning')
            return []

        # purge outdated connections, _ble_dl_files() refreshes this
        for key, value in list(ddh_ble.BLK_LIST.items()):
            if time.time() > value:
                ddh_ble.BLK_LIST.pop(key)
            else:
                yet = value - time.time()
                t = 'BLE: omit {} for {:.2f} s'
                signals.status.emit(t.format(key, yet))

        # build list w/ detected known macs NOT too recent
        loggers = []
        for dev in list_all_ble:
            d = dev.addr
            if d in ble_mac_filter and d not in ddh_ble.BLK_LIST:
                r = int(dev.rssi)
                if r > -90:
                    loggers.append(dev.addr)
                else:
                    text = 'BLE: {}, low signal {}'.format(dev.addr, r)
                    signals.status.emit(text)

        # show list of loggers to query
        s = 'BLE: {} loggers to query'
        signals.status.emit(s.format(len(loggers)))
        ddh_ble.LOGGERS_TO_QUERY = loggers
        signals.ble_scan_result.emit(loggers)
        return loggers

    @staticmethod
    def _ble_dl_loggers(signals):
        lc_ble = None
        dl_logger_ok = False

        # allow this to work on-demand
        if not ddh_ble.dl_flag:
            return

        # query every logger
        for counter, mac in enumerate(ddh_ble.LOGGERS_TO_QUERY):
            try:
                signals.status.emit('BLE: connecting {}'.format(mac))
                signals.ble_dl_session.emit(
                    mac, counter + 1, len(ddh_ble.LOGGERS_TO_QUERY))

                # download + restart logger
                with LoggerControllerBLE(mac) as lc_ble:
                    ddh_ble._ble_dl_files(lc_ble, signals, pre_rm=False)
                    lat, lon = DeckDataHubGPS.gps_get_last(signals)
                    s = 'N/A'
                    if lat and lon:
                        s = '{}{}'.format(lat, lon)
                    rv = lc_ble.command(RWS_CMD, s)
                    t = 'BLE: RWS {} = {}'.format(s, rv)
                    signals.status.emit(t)

                    # update HISTORY tab
                    signals.ble_deployed.emit(mac, lat, lon)

            except ble.BTLEException as be:
                # first Linux BLE interaction may fail
                signals.error.emit('BLE: exception {}'.format(be.message))
                e = 'Download error, retrying in {} s'
                e = e.format(ddh_ble.IGNORE_S)
                signals.error_gui.emit(e)
                signals.error.emit('BLE: ' + e)
                ddh_ble._ble_ignore_for(mac, ddh_ble.IGNORE_S)
            else:
                # everything ok, don't query again in long time
                ddh_ble._ble_ignore_for(mac, ddh_ble.FORGET_S)
                dl_logger_ok = True
            finally:
                signals.status.emit('BLE: disconnecting {}'.format(mac))
                if lc_ble:
                    lc_ble.close()

        signals.status.emit('BLE: all loggers done')
        signals.ble_dl_session_.emit('All loggers\ndone')
        return dl_logger_ok

    @staticmethod
    def _pre_dl_configuration(lc_ble, signals):
        signals.ble_dl_logger.emit()

        # how are you
        status = lc_ble.command(STATUS_CMD)
        signals.status.emit('BLE: STS = {}'.format(status))
        if not status:
            raise ble.BTLEException(status)

        # stop you, with string
        lat, lon = DeckDataHubGPS.gps_get_last(signals)
        s = 'N/A'
        if lat and lon:
            s = '{}{}'.format(lat, lon)
        ans = lc_ble.command(SWS_CMD, s)
        signals.status.emit('BLE: SWS {} = {}'.format(s, ans))
        if not ans:
            raise ble.BTLEException(status)

        # what time do you have
        logger_time = lc_ble.get_time()
        if not logger_time:
            print(logger_time)
            raise ble.BTLEException(logger_time)
        difference = datetime.datetime.now() - logger_time
        if abs(difference.total_seconds()) > 60:
            lc_ble.sync_time()
            signals.status.emit('BLE: GTM sync {}'.format(lc_ble.get_time()))
        else:
            signals.status.emit('BLE: GTM valid time')

        # RN4020 loggers: CC26x2 ones will ignore this
        control = 'BTC 00T,0006,0000,0064'
        ans = lc_ble.command(control)
        signals.status.emit('BLE: maybe RN4020 setup = {}'.format(ans))
        if not ans or b'ERR' in ans:
            raise ble.BTLEException(ans)

    @staticmethod
    def _pre_dl_ls(lc_ble, signals, pre_rm=False):
        # pre_rm = remove local files, useful for debug
        mac = lc_ble.per.addr
        if pre_rm:
            _rm_folder(mac)
            signals.warning.emit('SYS: local rm {} files'.format(mac))
        folder = _create_folder(mac)
        lid_files = lc_ble.ls_ext(b'lid')
        gps_files = lc_ble.ls_ext(b'gps')
        if lid_files == [b'ERR'] or gps_files == [b'ERR']:
            e = 'ls() returned ERR'
            raise ble.BTLEException(e)
        files = lid_files
        files.update(gps_files)
        signals.status.emit('BLE: ls = {}'.format(files))
        return folder, files

    # download files from this logger
    @staticmethod
    def _ble_dl_files(lc_ble, signals, pre_rm=False):
        # setup logger
        ddh_ble._pre_dl_configuration(lc_ble, signals)
        mac = lc_ble.address

        # list files
        folder, files = ddh_ble._pre_dl_ls(lc_ble, signals, pre_rm)
        num = 0
        name_n_size = {}
        total_size = 0

        # compare to local files to skip downloading existing ones
        for each in files.items():
            name = each[0]
            size = each[1]
            if not _exists_file(name, size, folder):
                name_n_size[name] = size
                num += 1
                total_size += size

        # download files one by one
        attempts = 0
        counter = 0
        total_left = total_size
        signals.status.emit('BLE: {} has {} files'.format(mac, num))
        for name, size in name_n_size.items():
            # statistics
            attempts += 1
            duration_logger = ((total_left // 5000) // 60) + 1
            total_left -= size
            signals.status.emit('BLE: get {}, {} B'.format(name, size))
            signals.ble_dl_file.emit(name, attempts, num, duration_logger)

            # x-modem file download, exceptions propagated to _ble_dl_loggers()
            start_time = time.time()
            if lc_ble.get_file(name, folder, size):
                signals.status.emit('BLE: got {}'.format(name))
            else:
                signals.status.emit('BLE: can\'t get {}'.format(name))

            # check received file ok
            if _exists_file(name, size, folder):
                counter += 1
                percent_x_size = (size / total_size) * 100
                speed = size / (time.time() - start_time)
                signals.ble_dl_file_.emit(percent_x_size, speed)

        # all files from this logger downloaded ok
        signals.ble_dl_logger_.emit(lc_ble.address, counter)


def _create_folder(folder_name):
    folder_name = 'dl_files/' + folder_name.replace(':', '-').lower() + '/'
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def _exists_file(file_name, size, folder_name):
    file_path = os.path.join(folder_name, file_name)
    if os.path.isfile(file_path):
        if os.path.getsize(file_path) == size:
            return True
    return False


def _rm_folder(mac):
    import shutil
    folder_name = 'dl_files/' + mac.replace(':', '-').lower() + '/'
    shutil.rmtree(folder_name, ignore_errors=True)


# shorten name
ddh_ble = DeckDataHubBLE
