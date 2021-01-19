import time
from settings import ctx
from threads.utils import wait_boot_signal
from threads.utils_aws import aws_get_credentials, aws_ddh_sync


PERIOD_AWS = 300


def loop(w, ev_can_i_boot):
    assert (PERIOD_AWS >= 30)
    wait_boot_signal(w, ev_can_i_boot, 'AWS')
    name, key_id, secret = aws_get_credentials()
    fol = str(ctx.app_dl_folder)

    while 1:
        if not ctx.aws_en:
            w.sig_aws.update('AWS: disabled')
            time.sleep(120)
            return

        ctx.sem_ble.acquire()
        ctx.sem_aws.acquire()
        w.sig_aws.status.emit('AWS: syncing {}'.format(fol))
        synced_files = aws_ddh_sync(name, key_id, secret, fol)
        s = 'OK' if type(synced_files) is list else 'ERR'
        w.sig_aws.update.emit('AWS {}'.format(s))
        ctx.sem_aws.release()
        ctx.sem_ble.release()
        time.sleep(PERIOD_AWS)
