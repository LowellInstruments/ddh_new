import time
from settings import ctx
from threads.utils_ftp import ftp_sync, emit_ftp_status, emit_ftp_update


class ThFTP:
    PERIOD_FTP = 300
    assert (PERIOD_FTP >= 30)

    def __init__(self, sig):
        # give time net thread to boot before ftp
        time.sleep(5)
        emit_ftp_status(sig, 'FTP: thread boot')

        while 1:
            if not ctx.ftp_en:
                emit_ftp_update(sig, 'FTP: disabled')
                time.sleep(5)
                continue

            if ctx.ble_ongoing:
                emit_ftp_status(sig, 'FTP: wait BLE to finish')
                time.sleep(5)
                continue

            ctx.ftp_ongoing = True
            ftp_sync(sig, ctx.dl_files_folder, ctx.app_conf_folder)
            ctx.ftp_ongoing = False
            p = self.PERIOD_FTP
            time.sleep(p)


def fxn(sig):
    ThFTP(sig)
