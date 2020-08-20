import os
from threads.utils import linux_ls_by_ext


cnv_test_fol = '~/PycharmProjects/ddh/dl_files/'


def emit_status(sig, s):
    if sig:
        sig.cnv_status.emit(s)


def emit_error(sig, e):
    if sig:
        sig.cnv_error.emit(e)


def _pre_rm_csv(fol, pre_rm=False):
    if not pre_rm:
        return
    ff = linux_ls_by_ext(fol, 'csv')
    for _ in ff:
        os.remove(_)
        print('removed {}'.format(os.path.basename(_)))
