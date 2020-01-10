import bluepy.btle as ble
import time
import os
import datetime
from mat.logger_controller import (
    STATUS_CMD,
    STOP_CMD,
    RWS_CMD,
    SWS_CMD
)
from mat.logger_controller_ble import (
    LoggerControllerBLE as LoggerControllerBLE
)
from apps.ddh_gps import DeckDataHubGPS


class DeckDataHubBLE:

    WANTED_FILE_TYPES = '.lid'
    B_LIST = {}
    FORGET_S = 600
    IGNORE_S = 30
    LOGGERS_TO_QUERY = []
    dl_flag = False

    @staticmethod
    def ble_toggle_dl():
        DeckDataHubBLE.dl_flag = not DeckDataHubBLE.dl_flag
        return DeckDataHubBLE.dl_flag

    @staticmethod
    def _ble_ignore_for(mac, seconds):
        DeckDataHubBLE.B_LIST[mac] = time.time() + seconds

    @staticmethod
    def ble_loop(signals, ble_mac_filter):
        while 1:
            if DeckDataHubBLE._ble_scan_loggers(signals, ble_mac_filter):
                DeckDataHubBLE._ble_dl_loggers(signals)
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
        for key, value in list(DeckDataHubBLE.B_LIST.items()):
            if time.time() > value:
                DeckDataHubBLE.B_LIST.pop(key)
            else:
                yet = value - time.time()
                t = 'BLE: {} omit for {:.2f} s'
                signals.status.emit(t.format(key, yet))

        # build list w/ detected known macs NOT too recent
        loggers = []
        for dev in list_all_ble:
            d = dev.addr
            if d in ble_mac_filter and d not in DeckDataHubBLE.B_LIST:
                r = int(dev.rssi)
                if r > -90:
                    loggers.append(dev.addr)
                else:
                    text = 'BLE: {}, low signal {}'.format(dev.addr, r)
                    signals.status.emit(text)

        # show list of loggers to query
        signals.status.emit('BLE: {} loggers to query'.format(len(loggers)))
        DeckDataHubBLE.LOGGERS_TO_QUERY = loggers
        signals.ble_scan_result.emit(loggers)
        return loggers

    @staticmethod
    def _ble_dl_loggers(signals):
        lc_ble = None
        dl_logger_ok = False

        # prevent this from working on-demand
        if not DeckDataHubBLE.dl_flag:
            return

        # query every logger
        for counter, mac in enumerate(DeckDataHubBLE.LOGGERS_TO_QUERY):
            try:
                signals.status.emit('BLE: connecting {}'.format(mac))
                signals.ble_dl_session.emit(
                    mac, counter + 1, len(DeckDataHubBLE.LOGGERS_TO_QUERY))

                # download + restart logger
                with LoggerControllerBLE(mac) as lc_ble:
                    DeckDataHubBLE._ble_dl_files(lc_ble, signals, pre_rm=False)
                    lat, lon = DeckDataHubGPS.gps_get_last()
                    s = ''
                    if lat and lon:
                        s = '{}{}'.format(lat, lon)
                    lc_ble.command(RWS_CMD, s)
                    t = 'BLE: RWS {}{}'.format(lat, lon)
                    signals.status.emit(t)
                    signals.ble_deployed.emit(mac, lat, lon)

            except ble.BTLEException as be:
                # first Linux BLE interaction may fail
                signals.error.emit('BLE: exception {}'.format(be.message))
                t = 'Download error, retrying in {} s'.format(DeckDataHubBLE.IGNORE_S)
                signals.error_gui.emit(t)
                signals.error.emit('BLE: ' + t)
                DeckDataHubBLE._ble_ignore_for(mac, DeckDataHubBLE.IGNORE_S)
            else:
                # everything ok
                DeckDataHubBLE._ble_ignore_for(mac, DeckDataHubBLE.FORGET_S)
                dl_logger_ok = True
            finally:
                signals.status.emit('BLE: disconnecting {}'.format(mac))
                if lc_ble:
                    lc_ble.close()

        signals.status.emit('BLE: all loggers done')
        signals.ble_dl_session_.emit('All loggers\ndone')
        return dl_logger_ok

    # download files from this logger
    @staticmethod
    def _ble_dl_files(lc_ble, signals, pre_rm=False):
        # setup logger
        DeckDataHubBLE._pre_dl_configuration(lc_ble, signals)
        mac = lc_ble.address

        # list files
        folder, files = DeckDataHubBLE._pre_dl_ls(lc_ble, signals, pre_rm)
        num = 0
        name_n_size = {}
        total_size = 0
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

    @staticmethod
    def _pre_dl_configuration(lc_ble, signals):
        signals.ble_dl_logger.emit()

        # how are you
        status = lc_ble.command(STATUS_CMD)
        signals.status.emit('BLE: status = {}'.format(status))
        if not status:
            raise ble.BTLEException(status)

        # stop you, with string
        lat, lon = DeckDataHubGPS.gps_get_last()
        s = ''
        if lat and lon:
            s = '{}{}'.format(lat, lon)
        answer = lc_ble.command(SWS_CMD, s)
        signals.status.emit('BLE: SWS {}{} = {}'.format(lat, lon, answer))
        if not answer:
            raise ble.BTLEException(status)

        # what time do you have
        logger_time = lc_ble.get_time()
        if not logger_time:
            raise ble.BTLEException(logger_time)
        difference = datetime.datetime.now() - logger_time
        if abs(difference.total_seconds()) > 60:
            lc_ble.sync_time()
            signals.status.emit('BLE: GTM sync {}'.format(lc_ble.get_time()))
        else:
            signals.status.emit('BLE: GTM valid time')

        # RN4020 loggers: CMD_CONTROL parameters BLE, CC26x2 ones will ignore this
        control = 'BTC 00T,0006,0000,0064'
        answer = lc_ble.command(control)
        signals.status.emit('BLE: maybe RN4020 setup = {}'.format(answer))
        if not answer or b'ERR' in answer:
            raise ble.BTLEException(answer)

    # files: list_lid_files() one logger
    @staticmethod
    def _pre_dl_ls(lc_ble, signals, pre_rm=False):
        # remove files, useful for debug, label ***
        mac = lc_ble.u.peripheral.addr
        if pre_rm:
            _rm_folder(mac)
            signals.warning.emit('SYS: local rm {} files'.format(mac))
        folder = _create_folder(mac)
        files = lc_ble.ls_lid()
        signals.status.emit('BLE: ls = {}'.format(files))
        return folder, files


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
