import time


class ButtonPressEvent:
    def __init__(self, code):
        self.code = code

    def key(self):
        return self.code


class DeckDataHubGUI:

    # sym = ('|', '/', '--', '\\', '|', '/', '--', '\\')
    sym = ('·', '··', '···', ' ')
    indicator = ''
    idx = 0

    @staticmethod
    def step_busy_indicator():
        ddh_gui.idx += 1
        ddh_gui.idx %= len(ddh_gui.sym)
        return ddh_gui.sym[ddh_gui.idx]

    @staticmethod
    def gui_loop(signals):
        while 1:
            ddh_gui.indicator = ddh_gui.step_busy_indicator()
            signals.gui_tick.emit(ddh_gui.indicator)
            time.sleep(1)


# shorten name
ddh_gui = DeckDataHubGUI