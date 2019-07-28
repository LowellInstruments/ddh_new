import bluepy.btle as ble
import time
import os
import datetime
from mat.logger_controller import (
    STATUS_CMD,
    STOP_CMD,
    RUN_CMD
)
from mat.logger_controller_ble_rn4020 import (
    LoggerControllerBLERN4020 as LoggerControllerBLE
)


class DeckDataHubBLE:

    WANTED_FILE_TYPES = '.lid'
    RECENTLY_DONE = {}
    FORGET = 600
    IGNORE = 30
    LOGGERS_TO_QUERY = []

    @staticmethod
    def _ble_add_mac_to_recent_connections(mac):
        DeckDataHubBLE.RECENTLY_DONE[mac] = time.time()

    @staticmethod
    def _ble_blacklist_some_time(mac, seconds):
        time_blacklisted = time.time() - DeckDataHubBLE.FORGET + seconds
        DeckDataHubBLE.RECENTLY_DONE[mac] = time_blacklisted

    @staticmethod
    def _ble_ignore_some_time(mac):
        DeckDataHubBLE._ble_blacklist_some_time(mac, DeckDataHubBLE.IGNORE)

    @staticmethod
    def ble_loop(signals, ble_mac_filter):
        while 1:
            if DeckDataHubBLE._ble_scan_loggers(signals, ble_mac_filter):
                DeckDataHubBLE._ble_dl_loggers(signals)
            time.sleep(2)

    @staticmethod
    def _ble_scan_loggers(signals, ble_mac_filter):
        signals.ble_scan_start.emit()
        signals.status.emit('BLE: detecting loggers...')
        try:
            list_all_ble = ble.Scanner().scan(3)
        except ble.BTLEException:
            signals.error_gui.emit('BLE: error scanning.')
            return []

        # purge outdated connections, _ble_dl_files() refreshes this
        for key, value in list(DeckDataHubBLE.RECENTLY_DONE.items()):
            if time.time() - value > DeckDataHubBLE.FORGET:
                DeckDataHubBLE.RECENTLY_DONE.pop(key)
            else:
                remaining_time = DeckDataHubBLE.FORGET - (time.time() - value)
                signals.status.emit('BLE: {} already queried, delay {:.2f} s.'.
                                    format(key, remaining_time))

        # build list w/ detected known macs NOT too recent
        loggers = []
        for dev in list_all_ble:
            if dev.addr in ble_mac_filter and\
                    dev.addr not in DeckDataHubBLE.RECENTLY_DONE:
                r = int(dev.rssi)
                if r > -90:
                    loggers.append(dev.addr)
                else:
                    text = 'BLE: {}, low signal {}'.format(dev.addr, r)
                    signals.status.emit(text)

        # show list of loggers to query
        signals.status.emit('BLE: {} loggers to query.'.format(len(loggers)))
        DeckDataHubBLE.LOGGERS_TO_QUERY = loggers
        signals.ble_scan_result.emit(loggers)
        return loggers

    @staticmethod
    def _ble_dl_loggers(signals):
        lc_ble = None
        dl_logger_ok = False

        # query every logger
        for counter, mac in enumerate(DeckDataHubBLE.LOGGERS_TO_QUERY):
            try:
                signals.status.emit('BLE: connecting {}.'.format(mac))
                signals.ble_dl_session.emit(
                    mac, counter + 1, len(DeckDataHubBLE.LOGGERS_TO_QUERY))
                with LoggerControllerBLE(mac) as lc_ble:
                    DeckDataHubBLE._ble_dl_files(lc_ble, signals)
            except ble.BTLEException:
                DeckDataHubBLE._ble_ignore_some_time(mac)
                break
            else:
                # ok, next
                DeckDataHubBLE._ble_add_mac_to_recent_connections(mac)
                dl_logger_ok = True
            finally:
                signals.status.emit('BLE: disconnecting {}.'.format(mac))
                if lc_ble:
                    lc_ble.close()

        signals.ble_dl_session_.emit('BLE: all loggers done.')
        return dl_logger_ok

    # download one entire logger
    @staticmethod
    def _ble_dl_files(lc_ble, signals):
        if not DeckDataHubBLE._ble_pre_dl_files(lc_ble, signals):
            mac = lc_ble.address
            signals.error_gui.emit('BLE: {} get error, wait 60 s.'.format(mac))
            raise ble.BTLEException

        # list files
        folder, files = DeckDataHubBLE._ble_list_files(lc_ble, signals)
        num = 0
        name_n_size = {}
        total_size = 0
        for each_file in files.items():
            name = each_file[0]
            size = each_file[1]
            if not do_we_have_this_file(name, size, folder):
                name_n_size[name] = size
                num += 1
                total_size += size

        # download one by one
        attempts = 0
        counter = 0
        total_left = total_size
        mac = lc_ble.address
        signals.status.emit('BLE: {} has {} files.'.format(mac, num))
        for name, size in name_n_size.items():
            # statistics
            attempts += 1
            duration_logger = ((total_left // 5000) // 60) + 1
            total_left -= size
            signals.status.emit('BLE: get {}, {} B.'.format(name, size))
            signals.ble_dl_file.emit(name, attempts, num, duration_logger)

            # XMODEM file download
            start_time = time.time()
            for retries in range(3):
                if lc_ble.get_file(name, folder, size):
                    signals.status.emit('BLE: got {}.'.format(name))
                    break
                else:
                    signals.status.emit('BLE: cannot get {}.'.format(name))
                    if retries == 2:
                        raise ble.BTLEException
                time.sleep(5)

            # check received file ok
            if do_we_have_this_file(name, size, folder):
                counter += 1
                percent_x_size = (size / total_size) * 100
                speed = size / (time.time() - start_time)
                signals.ble_dl_file_.emit(percent_x_size, speed)

        # RUN again this logger
        t = 'BLE: re-start = {}.'.format(lc_ble.command(RUN_CMD))
        signals.status.emit(t)
        signals.ble_dl_logger_.emit(lc_ble.address, counter)

    @staticmethod
    def _ble_pre_dl_files(lc_ble, signals):
        signals.ble_dl_logger.emit()

        status = lc_ble.command(STATUS_CMD)
        signals.status.emit('BLE: get status = {}.'.format(status))
        if not status:
            return False

        answer = lc_ble.command(STOP_CMD)
        signals.status.emit('BLE: stop deploy = {}.'.format(answer))
        if not answer:
            return False

        logger_time = lc_ble.get_time()
        if not logger_time:
            return False
        difference = datetime.datetime.now() - logger_time
        if abs(difference.total_seconds()) > 60:
            lc_ble.sync_time()
            signals.status.emit('BLE: sync {}.'.format(lc_ble.get_time()))
        else:
            signals.status.emit('BLE: logger time is up-to-date.')

        # logger: CMD_CONTROL parameters BLE
        control = 'BTC 00T,0006,0000,0064'
        answer = lc_ble.command(control)
        signals.status.emit('BLE: setup as = {}.'.format(answer))
        if not answer or b'ERR' in answer:
            return False

        # logger: all setup pre download is ok
        return True

    # files: list_lid_files() one logger
    @staticmethod
    def _ble_list_files(lc_ble, signals):
        folder = create_logger_folder(lc_ble.peripheral.addr)
        files = lc_ble.list_lid_files()
        signals.status.emit('BLE: logger DIR = {}.'.format(files))
        return folder, files


def create_logger_folder(folder_name):
    folder_name = 'dl_files/' + folder_name.replace(':', '-').lower() + '/'
    os.makedirs(folder_name, exist_ok=True)
    return folder_name


def do_we_have_this_file(file_name, size, folder_name):
    file_path = os.path.join(folder_name, file_name)
    if os.path.isfile(file_path):
        if os.path.getsize(file_path) == size:
            return True
    return False
