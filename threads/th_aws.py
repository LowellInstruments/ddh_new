import time
from settings import ctx


PERIOD_AWS = 300


def sync_files(w, dl_folder):
    w.sig_aws.status.emit('AWS: syncing {}'.format(dl_folder))


def loop(w):
    assert (PERIOD_AWS >= 30)
    w.sig_aws.status.emit('SYS: AWS thread started')

    while 1:
        if not ctx.aws_en:
            w.sig_aws.update('AWS: disabled')
            time.sleep(120)
            return

        # do not interrupt BLE
        ctx.sem_ble.acquire()
        ctx.sem_ble.release()

        # protect critical zone from NET thread
        ctx.sem_aws.acquire()
        sync_files(w, ctx.dl_folder)
        ctx.sem_aws.release()
        time.sleep(PERIOD_AWS)
