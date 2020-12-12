import time
from settings import ctx
from threads.utils import lid_to_csv, pre_rm_csv


PERIOD_CNV = 60


def loop(w, pre_rm=False):
    assert ctx.dl_files_folder
    assert PERIOD_CNV >= 30

    fol = str(ctx.dl_files_folder)
    pre_rm_csv(fol, pre_rm)

    while 1:
        # do not interrupt BLE or plotting
        ctx.sem_ble.acquire()
        ctx.sem_ble.release()
        ctx.sem_plt.acquire()
        ctx.sem_plt.release()

        # convert
        w.sig_cnv.status.emit('cnv thread')
        time.sleep(PERIOD_CNV)
        _, e = lid_to_csv(fol, 'DissolvedOxygen')
        # _, e = lid_to_csv(fol, 'Temperature')
        # _, e = lid_to_csv(fol, 'Pressure')
        w.sig_cnv.update.emit(e)
