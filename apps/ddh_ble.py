import json
from json import JSONDecodeError

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
import subprocess as sp


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
                if r >= -96:
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
    def _pre_dl_ls(lc, signals, pre_rm=False):
        # listing logger files
        # --------------------
        mac = _get_mac_from_lc(lc)
        if pre_rm:
            _rm_folder(mac)
            signals.warning.emit('SYS: local rm {} files'.format(mac))
        folder = _create_folder(mac)
        time.sleep(1)
        lid_files = lc.ls_ext(b'lid')
        time.sleep(1)
        gps_files = lc.ls_ext(b'gps')
        time.sleep(1)
        cfg_files = lc.ls_ext(b'cfg')
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
        mac = _get_mac_from_lc(lc)
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
    def _ble_dl_files(lc, sig, pre_rm=False):
        sig.ble_dl_logger.emit()
        # ddh_ble._rm_local_mat_cfg(lc)
        ddh_ble._ensure_stop_w_string(lc, sig)
        ddh_ble._logger_time_check(lc, sig)
        mac = _get_mac_from_lc(lc)

        # list files
        # ----------
        fol, files = ddh_ble._pre_dl_ls(lc, sig, pre_rm)
        num = 0
        name_n_size = {}
        total_size = 0
        for each in files.items():
            name, size = each[0], each[1]
            if size == 0:
                continue
            name_n_size[name] = size
            num += 1
            total_size += size

        # download logger files
        # ---------------------
        i = 0
        i_ok = 0
        total_left = total_size
        sig.status.emit('BLE: {} has {} files'.format(mac, num))
        ok = True
        for name, size in name_n_size.items():
            # stats
            i += 1
            duration_logger = ((total_left // 5000) // 60) + 1
            total_left -= size
            sig.status.emit('BLE: get {}, {} B'.format(name, size))
            sig.ble_dl_file.emit(name, i, num, duration_logger)

            # x-modem file download
            start_time = time.time()
            retries = 3
            while 1:
                if retries == 0:
                    e = 'exc GET {}'.format(__name__)
                    raise ble.BTLEException(e)

                if lc.get_file(name, fol, size):
                    break

                retries -= 1
                e = 'BLE: did not get {}, retries {}'.format(name, retries)
                sig.error.emit(e)
                time.sleep(5)

            # got file OK, update GUI
            sig.status.emit('BLE: got {}'.format(name))
            if _exists_file(name, size, fol):
                i_ok += 1
                percent_x_size = (size / total_size) * 100
                speed = size / (time.time() - start_time)
                sig.ble_dl_file_.emit(percent_x_size, speed)

            # remotely delete the file we got
            ddh_ble._rm_logger_file(lc, sig, name)

            # MAT.cfg left as it is
            if name.endswith('MAT.cfg'):
                continue

            # 2nd patch, get timestamp from .lid, .gps is the same
            attach_ts_to_file_names(fol, name, sig)

            # 1st patch, generate .lid, .gps files w/ timestamp
            # cp_org = os.path.join(os.getcwd(), fol, name)
            # t = time.time()
            # t_s = time.strftime("%Y%b%d_%H%M%S", time.localtime(t))
            # cp_dst = '_{}_{}'.format(t_s, name)
            # cp_dst = os.path.join(os.getcwd(), fol, cp_dst)
            #
            # # careful w/ names w/ parentheses, add extra \'
            # _cmd = 'cp \'{}\' \'{}\''.format(cp_org, cp_dst)
            # rv = sp.run(_cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
            # if rv.returncode != 0:
            #     sig.error.emit('BLE: error cp {}'.format(rv.stderr))
            # else:
            #     os.remove(cp_org)

        # all files from this logger downloaded ok
        sig.ble_dl_logger_.emit(lc.address, i_ok)
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
        mac = _get_mac_from_lc(lc)
        mac = mac.replace(':', '-')
        try:
            path = os.path.join('dl_files', mac, 'MAT.cfg')
            with open(path) as f:
                cfg_dict = json.load(f)
            _ = 'using own MAT.cfg for {}'.format(mac)
            sig.status.emit('BLE: {}'.format(_))
        except (JSONDecodeError, FileNotFoundError):
            cfg_dict = None
            _ = 'no own MAT.cfg for {}'.format(mac)
            sig.status.emit('BLE: {}'.format(_))

        # no MAT.cfg for this logger, or error, try backup one
        if not cfg_dict:
            src = os.path.join('settings', 'MAT_def_DO.cfg')
            dst = os.path.join('dl_files', mac, 'MAT.cfg')
            _ = 'cp {} {}'.format(src, dst)
            rv = sp.run(_, shell=True, stdout=sp.PIPE)
            if rv.returncode != 0:
                e = 'no default MAT.cfg for {}'.format(mac)
                raise ble.BTLEException(e)
            _ = 'using default MAT.cfg for {}'.format(mac)
            sig.status.emit('BLE: {}'.format(_))

        # formatting, if we here, everything ok
        # -------------------------------------
        a = lc.command('FRM')
        if a != [b'FRM', b'00']:
            e = 'exc {} FRM'.format(__name__)
            raise ble.BTLEException(e)
        sig.status.emit('BLE: FRM = {}'.format(a))
        time.sleep(2)

        # reconfiguring logger
        # --------------------
        a = lc.send_cfg(cfg_dict)
        if a != [b'CFG', b'00']:
            sig.status.emit('BLE: CFG = {}'.format(a))
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
    p = os.path.join(os.getcwd(), folder_name, file_name)
    if os.path.isfile(p):
        if os.path.getsize(p) == size:
            return True
    return False


def _get_mac_from_lc(lc):
    try:
        return lc.per.addr
    except (AttributeError, Exception):
        e = 'exc mac {}'.format(__name__)
        raise ble.BTLEException(e)


def _rm_folder(mac):
    import shutil
    folder_name = 'dl_files/' + mac.replace(':', '-').lower() + '/'
    shutil.rmtree(folder_name, ignore_errors=True)


def _put_lid_ts_to_tmp(dst):
    t = time.time()
    t_s = time.strftime("%Y%b%d_%H%M%S", time.localtime(t))
    with open(dst, 'w+') as f:
        f.write(t_s)
    return t_s


def _get_ts_from_tmp(org):
    # in case no .tmp file to extract ts, create it
    if not os.path.isfile(org):
        t = time.time()
        t_s = time.strftime("XX_%Y%b%d_%H%M%S", time.localtime(t))
        return t_s

    # such .tmp file exists, 16 == len(%Y%b%d_%H%M%S)
    with open(org, 'r') as f:
        t_s = f.readline(16)
        return t_s


def attach_ts_to_file_names(fol, name, sig):
    # org -> fol/<name>.lid, fol/<name>.gps
    org = os.path.join(os.getcwd(), fol, name)

    # dst -> fol/<name>_ts.lid, fol/<name>_ts.gps
    dst = None

    # tmp -> /fol/.<name>.tmp, note heading dot
    tmp = '.{}.tmp'.format(name.split('.')[0])
    tmp = os.path.join(os.getcwd(), fol, tmp)

    # .lid: write t_s to tmp, .gps: read t_s from tmp
    if name.endswith('lid'):
        t_s = _put_lid_ts_to_tmp(tmp)
        dst = '{}-{}.lid'.format(name.split('.')[0], t_s)
    if name.endswith('gps'):
        t_s = _get_ts_from_tmp(tmp)
        # dst -> fol/<name>_ts.gps, XX if no .tmp
        dst = '{}-{}.gps'.format(name.split('.')[0], t_s)

    # dst -> fol/<name>_ts.lid, fol/<name>_ts.gps
    dst = os.path.join(os.getcwd(), fol, dst)
    _cmd = 'cp \'{}\' \'{}\''.format(org, dst)
    rv = sp.run(_cmd, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)
    if rv.returncode != 0:
        sig.error.emit('BLE: error cp {}'.format(rv.stderr))
    else:
        os.remove(org)


# shorten name
ddh_ble = DeckDataHubBLE
