def emit_time_status(sig, s):
    if sig:
        sig.status.emit(s)


def emit_time_gui_update(sig, b):
    if sig:
        sig.update.emit(b)
