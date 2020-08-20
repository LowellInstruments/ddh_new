import time

from threads.utils_lif import emit_status, emit_beat


class ButtonPressEvent:
    def __init__(self, code):
        self.code = code

    def key(self):
        return self.code


class ThLife:

    sym = ('·', '··', '···', ' ')
    idx = 0

    # heartbeat with signals
    def __init__(self, sig):
        self.sig = sig
        emit_status(self.sig, 'LIF: thread boot')

        while 1:
            emit_beat(sig, self.sym[self.idx])
            self.idx = (self.idx + 1) % len(self.sym)
            time.sleep(1)


def fxn(sig):
    ThLife(sig)

