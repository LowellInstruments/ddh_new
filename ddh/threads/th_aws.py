import time
from ddh.settings import ctx
from ddh.threads.utils import wait_boot_signal
from ddh.threads.utils_aws import aws_get_credentials, aws_ddh_sync


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
        sig = w.sig_aws.error
        synced_files = aws_ddh_sync(name, key_id, secret, fol, sig)
        s = 'OK' if type(synced_files) is list else 'ERR'
        w.sig_aws.update.emit('AWS {}'.format(s))
        ctx.sem_aws.release()
        ctx.sem_ble.release()
        synced_files = [] if synced_files is None else synced_files
        for each in synced_files:
            w.sig_aws.status.emit('AWS: uploaded {}'.format(each))
        time.sleep(PERIOD_AWS)
