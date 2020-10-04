import time

from threads.utils_time import emit_time_status, emit_time_gui_update


class ButtonPressEvent:
    def __init__(self, code):
        self.code = code

    def key(self):
        return self.code


class ThTime:

    sym = ('·', '··', '···', ' ')
    idx = 0

    # heartbeat with signals
    def __init__(self, sig):
        self.sig = sig
        emit_time_status(self.sig, 'TIM: thread boot')

        while 1:
            emit_time_gui_update(sig, self.sym[self.idx])
            self.idx = (self.idx + 1) % len(self.sym)
            time.sleep(1)


def fxn(sig):
    ThTime(sig)

