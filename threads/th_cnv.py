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
            if ctx.ble_ongoing:
                emit_cnv_status(sig, 'CNV: wait BLE to finish')
                time.sleep(5)
                continue

            if ctx.plt_ongoing:
                emit_cnv_status(sig, 'CNV: wait PLT to finish')
                time.sleep(5)
                continue

            lid_to_csv(fol)
            time.sleep(self.PERIOD_CNV)


if __name__ == '__main__':
    # don't put dots './' or '../'in this path
    ThCNV(None)
