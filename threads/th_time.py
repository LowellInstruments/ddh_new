import time


class ButtonPressEvent:
    def __init__(self, code):
        self.code = code

    def key(self):
        return self.code


def loop(w):
    symbols = ('·', '··', '···', ' ')
    idx = 0
    w.sig_tim.status.emit('SYS: TIM thread started')

    while 1:
        idx = (idx + 1) % len(symbols)
        w.sig_tim.update.emit(symbols[idx])
        time.sleep(1)
