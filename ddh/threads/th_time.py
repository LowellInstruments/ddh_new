import time
from ddh.settings import ctx
from ddh.threads.utils import wait_boot_signal
from ddh.threads.utils_time import utils_time_update_datetime_source


class ButtonPressEvent:
    def __init__(self, code):
        self.code = code

    def key(self):
        return self.code


TIME_SYNC_PERIOD_S = 600


def loop(w, ev_can_i_boot):
    """ basically, updates some GUI fields """

    assert TIME_SYNC_PERIOD_S > 120

    # maybe th_time does not need to be blocked
    # wait_boot_signal(w, ev_can_i_boot, 'TIM')

    symbols = ('·', '··', '···', ' ')
    idx = 0
    steps = 0

    while 1:
        # some long operations like plotting show 3 dots
        time.sleep(1)
        steps += 1
        idx = (idx + 1) % len(symbols)
        w.sig_tim.update.emit(symbols[idx])

        # things to do often but not always
        if ctx.sem_ble.acquire(blocking=False):
            if steps >= TIME_SYNC_PERIOD_S:
                steps = 0
                utils_time_update_datetime_source(w)
            ctx.sem_ble.release()
