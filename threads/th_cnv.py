import time
from settings import ctx
from threads import utils_cnv
from threads.utils import lid_to_csv, _pre_rm_csv
from threads.utils_cnv import (
    emit_cnv_status)


def fxn(sig):
    ThCNV(sig)


class ThCNV:
    PERIOD_CNV = 60
    assert (PERIOD_CNV >= 30)

    def __init__(self, sig):

        # know our folder
        fol = utils_cnv.cnv_test_fol
        if ctx.dl_files_folder:
            fol = ctx.dl_files_folder
        fol = str(fol)
        _pre_rm_csv(fol, pre_rm=False)

        # loop
        s = 'CNV: thread boot, folder {}'.format(fol)
        emit_cnv_status(sig, s)

        while 1:
            # do not interrupt BLE or plotting
            ctx.sem_ble.acquire()
            ctx.sem_ble.release()
            ctx.sem_plt.acquire()
            ctx.sem_plt.release()

            # add all the ones you want
            lid_to_csv(fol, 'DissolvedOxygen')
            # lid_to_csv(fol, 'Temperature')
            # lid_to_csv(fol, 'Pressure')
            time.sleep(self.PERIOD_CNV)


if __name__ == '__main__':
    # don't put dots './' or '../'in this path
    ThCNV(None)
