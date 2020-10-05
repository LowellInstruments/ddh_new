cnv_test_fol = '~/PycharmProjects/ddh/dl_files/'


def emit_cnv_status(sig, s):
    if sig:
        sig.cnv_status.emit(s)


def emit_cnv_update(sig, u):
    if sig:
        sig.cnv_update.emit(u)
