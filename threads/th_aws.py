import time
from settings import ctx
from threads.utils import wait_boot_signal

PERIOD_AWS = 300


def sync_files(w, dl_folder):
    w.sig_aws.status.emit('AWS: syncing {}'.format(dl_folder))
    w.sig_aws.update.emit('AWS OK')


def loop(w, ev_can_i_boot):
    assert (PERIOD_AWS >= 30)
    wait_boot_signal(w, ev_can_i_boot, 'AWS')

    while 1:
        if not ctx.aws_en:
            w.sig_aws.update('AWS: disabled')
            time.sleep(120)
            return

        ctx.sem_ble.acquire()
        ctx.sem_aws.acquire()
        sync_files(w, ctx.dl_folder)
        ctx.sem_aws.release()
        ctx.sem_ble.release()
        time.sleep(PERIOD_AWS)
