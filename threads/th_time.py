import time
from settings import ctx
from threads.utils import wait_boot_signal
from threads.utils_time import time_via


class ButtonPressEvent:
    def __init__(self, code):
        self.code = code

    def key(self):
        return self.code


TIME_SYNC_PERIOD_S = 300


def loop(w, ev_can_i_boot):
    assert TIME_SYNC_PERIOD_S > 120
    wait_boot_signal(w, ev_can_i_boot, 'TIM')

    symbols = ('·', '··', '···', ' ')
    idx = 0
    steps = 0

    while 1:
        time.sleep(1)
        steps += 1
        idx = (idx + 1) % len(symbols)
        w.sig_tim.update.emit(symbols[idx])


        # things to do often but not always
        if ctx.sem_ble.acquire(blocking=False):
            if steps >= TIME_SYNC_PERIOD_S:
                steps = 0
                time_via(w)
            ctx.sem_ble.release()
