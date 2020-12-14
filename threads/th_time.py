import time
from settings import ctx
from threads.utils_time import time_sync_net, time_sync_gps


class ButtonPressEvent:
    def __init__(self, code):
        self.code = code

    def key(self):
        return self.code


TIME_SYNC_PERIOD_S = 300


def time_via(w):
    via = 'local'
    if time_sync_gps():
        via = 'GPS'
    elif time_sync_net():
        via = 'NTP'
    w.sig_tim.status.emit('TIM: sync {}'.format(via))
    w.sig_tim.via.emit(via)


def loop(w):
    assert TIME_SYNC_PERIOD_S > 120
    symbols = ('·', '··', '···', ' ')
    idx = 0
    w.sig_tim.status.emit('SYS: TIM thread started')
    steps = 0

    while 1:
        time.sleep(1)
        steps += 1
        idx = (idx + 1) % len(symbols)
        w.sig_tim.update.emit(symbols[idx])


        # things to do often but not always
        ctx.sem_ble.acquire()
        ctx.sem_ble.release()
        if steps == TIME_SYNC_PERIOD_S:
            steps = 0
            time_via(w)
