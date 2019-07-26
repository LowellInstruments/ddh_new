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
        except ble.BTLEException as btle_ex:
            signals.error_gui.emit(btle_ex.message)
            return []

        # purge old connections, _ble_dl_files() adds new ones at the end
        for key, value in list(DeckDataHubBLE.RECENTLY_DONE.items()):
            if time.time() - value > DeckDataHubBLE.FORGET:
                DeckDataHubBLE.RECENTLY_DONE.pop(key)
            else:
                remaining_time = DeckDataHubBLE.FORGET - (time.time() - value)
                signals.status.emit('BLE: {} recently queried, delay {:.2f} s.'.
                                    format(key, remaining_time))

        # build list with detected known macs NOT too recent
        loggers = []
        for dev in list_all_ble:
            rssi = int(dev.rssi)
            if dev.addr in ble_mac_filter and\
                    dev.addr not in DeckDataHubBLE.RECENTLY_DONE:
                if rssi > -90:
                    loggers.append(dev.addr)
                else:
                    text = 'BLE: low RSSI {} for {}'.format(rssi, dev.addr)
                    signals.status.emit(text)

        # update the global list of loggers to query
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
                er = 'BLE: error, retrying in {} 60 s.'.format(mac)
                signals.error_gui.emit(er)
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

    # files: download one logger
    @staticmethod
    def _ble_dl_files(lc_ble, signals):
        if not DeckDataHubBLE._ble_pre_dl_files(lc_ble, signals):
            raise ble.BTLEException('Could not setup logger for download')

        # files: listing them
        folder, files = DeckDataHubBLE._ble_list_files(lc_ble, signals)
        num_files_to_download = 0
        pairs_to_download = {}
        total_size = 0
        for name_n_size in files.items():
            name = name_n_size[0]
            size = name_n_size[1]
            if not do_we_have_this_file(name, size, folder):
                pairs_to_download[name] = size
                num_files_to_download += 1
                total_size += size

        # files: banner
        counter_file_dl_attempts = 0
        counter_file_dl_ok = 0
        total_left = total_size
        signals.status.emit('BLE: {} files to download from {}.'
                            .format(num_files_to_download, lc_ble.address))

        # files: get one by one
        for name, size in pairs_to_download.items():
            counter_file_dl_attempts += 1
            duration_logger = ((total_left // 5000) // 60) + 1
            total_left -= size
            signals.status.emit('BLE: get {}, {} B.'.format(name, size))
            signals.ble_dl_file.emit(name,
                                     counter_file_dl_attempts,
                                     num_files_to_download,
                                     duration_logger)

            # xmodem file download
            start_time = time.time()
            for retries in range(3):
                result_dl_file = lc_ble.get_file(name, folder, size)
                if result_dl_file:
                    signals.status.emit('BLE: got {} ok.'.format(name))
                    break
                else:
                    signals.status.emit('BLE: cannot get {}.'.format(name))
                    if retries == 2:
                        raise ble.BTLEException
                time.sleep(5)

            # check the received file is ok
            if do_we_have_this_file(name, size, folder):
                counter_file_dl_ok += 1
                percent_x_size = (size / total_size) * 100
                speed = size / (time.time() - start_time)
                signals.ble_dl_file_.emit(percent_x_size, speed)

        # RUN again this logger
        t = 'BLE: re-start = {}.'.format(lc_ble.command(RUN_CMD))
        signals.status.emit(t)
        signals.ble_dl_logger_.emit(lc_ble.address, counter_file_dl_ok)

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
