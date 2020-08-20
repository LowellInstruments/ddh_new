import time
from context import ctx
from threads import utils_cnv
from threads.utils import lid_to_csv
from threads.utils_cnv import (
    emit_status, _pre_rm_csv, emit_error)


def fxn(sig):
    ThCNV(sig)


class ThCNV:
    def __init__(self, sig):

        # know our folder
        fol = utils_cnv.cnv_test_fol
        if ctx.dl_files_folder:
            fol = ctx.dl_files_folder
        fol = str(fol)
        _pre_rm_csv(fol, pre_rm=False)

        # loop
        s = 'CNV: thread launched, folder {}'.format(fol)
        emit_status(sig, s)

        while 1:
            if ctx.ble_ongoing:
                # emit_status(sig, 'CNV: wait BLE to finish')
                time.sleep(5)
                continue

            if ctx.plt_ongoing:
                emit_status(sig, 'CNV: wait PLT to finish')
                time.sleep(5)
                continue

            if not lid_to_csv(fol):
                emit_error(sig, 'CNV: some error')

            time.sleep(5)


if __name__ == '__main__':
    # don't put dots './' or '../'in this path
    ThCNV(None)
