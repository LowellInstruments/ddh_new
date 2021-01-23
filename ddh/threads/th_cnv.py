import time
from ddh.settings import ctx
from ddh.threads.utils import lid_to_csv, pre_rm_csv, wait_boot_signal

PERIOD_CNV = 60


def loop(w, ev_can_i_boot, pre_rm=False):
    assert PERIOD_CNV >= 30
    assert ctx.app_dl_folder
    wait_boot_signal(w, ev_can_i_boot, 'CNV')

    fol = str(ctx.app_dl_folder)
    pre_rm_csv(fol, pre_rm)

    while 1:
        ctx.sem_ble.acquire()
        ctx.sem_plt.acquire()
        _, e = lid_to_csv(fol, '_DissolvedOxygen')
        # _, e = lid_to_csv(fol, '_Temperature')
        # _, e = lid_to_csv(fol, '_Pressure')
        w.sig_cnv.update.emit(e)
        ctx.sem_plt.release()
        ctx.sem_ble.release()
        time.sleep(PERIOD_CNV)

