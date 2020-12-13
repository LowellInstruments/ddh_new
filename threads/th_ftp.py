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

            if not ctx.aws_en:
                emit_ftp_update(sig, 'FTP: disabled')
                time.sleep(120)
                continue

            # do not interrupt BLE
            ctx.sem_ble.acquire()
            ctx.sem_ble.release()

            ctx.sem_aws.acquire()
            ftp_sync(sig, ctx.dl_folder, ctx.app_conf_folder)
            ctx.sem_aws.release()
            p = self.PERIOD_FTP
            time.sleep(p)


def fxn(sig):
    ThFTP(sig)
