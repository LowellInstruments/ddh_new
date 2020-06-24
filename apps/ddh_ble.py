import json
from shutil import copyfile
import bluepy.btle as ble
import time
import os
import datetime
from mat.logger_controller import (
    STATUS_CMD,
    RWS_CMD,
    SWS_CMD, DEL_FILE_CMD
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

    # starts GUI with BLE downloading (en)disabled
    dl_flag = True

    @staticmethod
    def ble_toggle_dl():
        ddh_ble.dl_flag = not ddh_ble.dl_flag
        return ddh_ble.dl_flag

    @staticmethod
    def _ble_ignore_for(mac, seconds):
        ddh_ble.BLK_LIST[mac] = time.time() + seconds

    @staticmethod
    def _ble_scan_loggers(signals, ble_mac_filter):
        signals.ble_scan_start.emit()
        try:
            scanner = ble.Scanner()
            list_all_ble = scanner.scan(5.0)
        except ble.BTLEException:
            signals.error.emit('BLE: error scanning')
            return []

        # purge outdated connections
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
                if r >= -93:
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
    def _ensure_stop_w_string(lc, signals):
        # get GPS coordinates
        # -------------------
        lat, lon = DeckDataHubGPS.gps_get_last(signals)
        s = 'N/A'
        if lat and lon:
            s = '{}{}'.format(lat, lon)

        # try to stop with string
        # -------------------------
        till = time.perf_counter() + 10
        while 1:
            if time.perf_counter() > till:
                e = 'exc SWS {}'.format(__name__)
                raise ble.BTLEException(e)

            a = lc.command(STATUS_CMD)
            signals.status.emit('BLE: STS = {}'.format(a))
            if a == [b'STS', b'0201']:
                return

            if a == [b'BSY']:
                continue

            a = lc.command(SWS_CMD, s)
            signals.status.emit('BLE: SWS {} = {}'.format(s, a))

    @staticmethod
    def _logger_time_check(lc, sig=None):
        # command: GTM
        # ------------
        t = lc.get_time()
        sig.status.emit('BLE: GTM {}'.format(t))
        if t is None:
            e = 'exc GTM {}'.format(__name__)
            raise ble.BTLEException(e)

        # command: STM only if needed
        # ---------------------------
        d = datetime.datetime.now() - t
        s = 'time sync not needed'
        if abs(d.total_seconds()) > 60:
            a = lc.sync_time()
            if a != [b'STM', b'00']:
                e = 'exc STM {}'.format(__name__)
                raise ble.BTLEException(e)
            s = 'time synced {}'.format(lc.get_time())
        sig.status.emit('BLE: STM {}'.format(s))

    @staticmethod
    def _pre_dl_ls(lc_ble, signals, pre_rm=False):
        # listing logger files
        # --------------------
        mac = lc_ble.per.addr
        if pre_rm:
            _rm_folder(mac)
            signals.warning.emit('SYS: local rm {} files'.format(mac))
        folder = _create_folder(mac)
        lid_files = lc_ble.ls_ext(b'lid')
        gps_files = lc_ble.ls_ext(b'gps')
        cfg_files = lc_ble.ls_ext(b'cfg')
        if lid_files == [b'ERR']:
            e = 'exc DIR_LID {}'.format(__name__)
            raise ble.BTLEException(e)
        if gps_files == [b'ERR']:
            e = 'exc DIR_GPS {}'.format(__name__)
            raise ble.BTLEException(e)
        if cfg_files == [b'ERR']:
            e = 'exc DIR_CFG {}'.format(__name__)
            raise ble.BTLEException(e)
        files = lid_files
        files.update(gps_files)
        files.update(cfg_files)
        signals.status.emit('BLE: ls = {}'.format(files))
        return folder, files

    @staticmethod
    def _rm_local_mat_cfg(lc):
        mac = lc.per.addr
        mac = mac.replace(':', '-')
        try:
            path = os.path.join('dl_files', mac, 'MAT.cfg')
            os.remove(path)
        except OSError as os_e:
            # print('logger has no previous MAT.cfg')
            pass

    @staticmethod
    def _rm_logger_file(lc, sig, name):
        if name == 'MAT.cfg':
            return
        a = lc.command(DEL_FILE_CMD, name)
        if a != [b'DEL', b'00']:
            e = 'exc RM {}'.format(__name__)
            raise ble.BTLEException(e)
        sig.status.emit('BLE: DEL = {}'.format(a))

    @staticmethod
    def _ble_dl_files(lc, signals, pre_rm=False):
        signals.ble_dl_logger.emit()
        ddh_ble._rm_local_mat_cfg(lc)
        ddh_ble._ensure_stop_w_string(lc, signals)
        ddh_ble._logger_time_check(lc, signals)
        mac = lc.per.addr

        # list files
        # ----------
        folder, files = ddh_ble._pre_dl_ls(lc, signals, pre_rm)
        num = 0
        name_n_size = {}
        total_size = 0
        for each in files.items():
            name = each[0]
            size = each[1]
            if size == 0:
                continue
            if _exists_file(name, size, folder):
                continue
            name_n_size[name] = size
            num += 1
            total_size += size

        # download logger files
        # ---------------------
        attempts = 0
        counter = 0
        total_left = total_size
        signals.status.emit('BLE: {} has {} files'.format(mac, num))
        ok = True
        for name, size in name_n_size.items():
            # stats
            attempts += 1
            duration_logger = ((total_left // 5000) // 60) + 1
            total_left -= size
            signals.status.emit('BLE: get {}, {} B'.format(name, size))
            signals.ble_dl_file.emit(name, attempts, num, duration_logger)

            # x-modem file download, exceptions propagated to _ble_dl_loggers()
            start_time = time.time()
            cp_bak = None
            if lc.get_file(name, folder, size):
                signals.status.emit('BLE: got {}'.format(name))

                # delete file from logger
                ddh_ble._rm_logger_file(lc, signals, name)

                # generate files with timestamp
                if not name.endswith('MAT.cfg'):
                    t = time.time()
                    t_s = time.strftime("%Y%b%d_%H%M%S", time.localtime(t))
                    cp_org = '{}/{}'.format(folder, name)
                    cp_bak = cp_org
                    cp_dst = '{}/_{}_{}'.format(folder, t_s, name)
                    copyfile(cp_org, cp_dst)

            if _exists_file(name, size, folder):
                if cp_bak and not name.endswith('MAT.cfg'):
                    os.remove(cp_bak)
                counter += 1
                percent_x_size = (size / total_size) * 100
                speed = size / (time.time() - start_time)
                signals.ble_dl_file_.emit(percent_x_size, speed)

        # all files from this logger downloaded ok
        signals.ble_dl_logger_.emit(lc.address, counter)
        return ok

    @staticmethod
    def _ensure_run_w_string(lc, sig):
        mac = lc.address
        lat, lon = DeckDataHubGPS.gps_get_last(sig)
        s = 'N/A'
        if lat and lon:
            s = '{}{}'.format(lat, lon)

        # status, should be running
        # -------------------------
        till = time.perf_counter() + 20
        while 1:
            if time.perf_counter() > till:
                e = 'exc RWS {}'.format(__name__)
                raise ble.BTLEException(e)

            a = lc.command(STATUS_CMD)
            sig.status.emit('BLE: STS = {}'.format(a))
            if a == [b'STS', b'0200']:
                break
            if a == [b'STS', b'0203']:
                break
            if a == [b'BSY']:
                continue
            if a is None:
                continue

            a = lc.command(RWS_CMD, s)
            sig.status.emit('BLE: RWS {} = {}'.format(s, a))

        # update history tab
        # ------------------
        ddh_ble._update_history_tab(mac, sig, lat, lon)

    @staticmethod
    def _logger_re_setup(lc, sig):
        # checking we have this logger MAT.cfg
        # -------------------------------------
        mac = lc.per.addr
        mac = mac.replace(':', '-')
        try:
            path = os.path.join('dl_files', mac, 'MAT.cfg')
            with open(path) as f:
                cfg_dict = json.load(f)
        except FileNotFoundError:
            e = 'exc no MAT.cfg to restore? {}'.format(__name__)
            raise ble.BTLEException(e)

        if not cfg_dict:
            e = 'exc {}'.format(__name__)
            raise ble.BTLEException(e)

        # formatting, if we here, everything ok
        # -------------------------------------
        a = lc.command('FRM')
        if a != [b'FRM', b'00']:
            e = 'exc {} FRM'.format(__name__)
            raise ble.BTLEException(e)
        sig.status.emit('BLE: FRM = {}'.format(a))

        # reconfiguring logger
        # --------------------
        a = lc.send_cfg(cfg_dict)
        if a != [b'CFG', b'00']:
            e = 'exc {} CFG'.format(__name__)
            raise ble.BTLEException(e)
        sig.status.emit('BLE: CFG = {}'.format(a))

    # super function
    # ===============
    @staticmethod
    def _ble_dl_loggers(sig):
        lc = None
        dl_logger_ok = False

        # allow this to work on-demand
        if not ddh_ble.dl_flag:
            return

        # query every logger
        for counter, mac in enumerate(ddh_ble.LOGGERS_TO_QUERY):
            try:
                sig.status.emit('BLE: connecting {}'.format(mac))
                sig.ble_dl_session.emit(
                    mac, counter + 1, len(ddh_ble.LOGGERS_TO_QUERY))

                # download + restart logger
                with LoggerControllerBLE(mac) as lc:
                    ok = ddh_ble._ble_dl_files(lc, sig, pre_rm=False)
                    if ok:
                        ddh_ble._logger_re_setup(lc, sig)
                        ddh_ble._ensure_run_w_string(lc, sig)
            except ble.BTLEException as be:
                # first Linux BLE interaction may fail
                sig.error.emit('BLE: exception {}'.format(be.message))
                e = 'Download error, retrying in {} s'
                e = e.format(ddh_ble.IGNORE_S)
                sig.error_gui.emit(e)
                sig.error.emit('BLE: ' + e)
                ddh_ble._ble_ignore_for(mac, ddh_ble.IGNORE_S)
            else:
                # everything ok, don't query again in long time
                ddh_ble._ble_ignore_for(mac, ddh_ble.FORGET_S)
                dl_logger_ok = True
            finally:
                sig.status.emit('BLE: disconnecting {}'.format(mac))
                if lc:
                    lc.close()

        sig.status.emit('BLE: all loggers done')
        sig.ble_dl_session_.emit('All loggers\ndone')
        return dl_logger_ok

    @staticmethod
    def _update_history_tab(mac, sig, lat, lon):
        sig.ble_deployed.emit(mac, lat, lon)

    @staticmethod
    def ble_loop(signals, ble_mac_filter):
        while 1:
            if ddh_ble._ble_scan_loggers(signals, ble_mac_filter):
                ddh_ble._ble_dl_loggers(signals)
            time.sleep(2)


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
