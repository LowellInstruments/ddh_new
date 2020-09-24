def emit_time_status(sig, s):
    if sig:
        sig.time_status.emit(s)


def emit_time_gui_update(sig, b):
    if sig:
        sig.time_update.emit(b)
