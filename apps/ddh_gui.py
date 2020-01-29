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
        DeckDataHubGUI.idx += 1
        DeckDataHubGUI.idx %= len(DeckDataHubGUI.sym)
        return DeckDataHubGUI.sym[DeckDataHubGUI.idx]

    @staticmethod
    def gui_loop(signals):
        while 1:
            DeckDataHubGUI.indicator = DeckDataHubGUI.step_busy_indicator()
            signals.gui_tick.emit(DeckDataHubGUI.indicator)
            time.sleep(1)
