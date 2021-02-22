import time
from ddh.settings import ctx
from ddh.threads.utils import wait_boot_signal
from ddh.threads.utils_aws import aws_credentials_get, aws_ddh_sync


PERIOD_AWS = 300


def loop(w, ev_can_i_boot):
    assert (PERIOD_AWS >= 30)
    wait_boot_signal(w, ev_can_i_boot, 'AWS')
    name, key_id, secret = aws_credentials_get()
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

        # sf means 'synced_files'
        sf = aws_ddh_sync(name, key_id, secret, fol, sig)
        s = 'OK' if type(sf) is list else 'ERR'
        w.sig_aws.update.emit('AWS {}'.format(s))
        ctx.sem_aws.release()
        ctx.sem_ble.release()

        sf = [] if sf is None else sf
        for each in sf:
            w.sig_aws.status.emit('AWS: uploaded {}'.format(each))
        time.sleep(PERIOD_AWS)


# for testing purposes
if __name__ == '__main__':
    i = 0
    _an_, _ak_, _as_ = aws_credentials_get()
    src_dir = '.'
    while 1:
        print('\nmain iteration #{}'.format(i))
        i += 1
        ff = aws_ddh_sync(_an_, _ak_, _as_, src_dir, None)
        ff = [] if ff is None else ff
        for f in ff:
            print(f)
        time.sleep(30)

