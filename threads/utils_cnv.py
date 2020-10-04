cnv_test_fol = '~/PycharmProjects/ddh/dl_files/'


def emit_cnv_status(sig, s):
    if sig:
        sig.cnv_status.emit(s)


def emit_cnv_error(sig, e):
    if sig:
        sig.cnv_error.emit(e)


def emit_cnv_update(sig, u):
    remove all cnv signals
    if sig:
        sig.cnv_update.emit(u)
