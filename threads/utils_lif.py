def emit_status(sig, s):
    if sig:
        sig.lif_status.emit(s)


def emit_beat(sig, b):
    if sig:
        sig.lif_beat.emit(b)
