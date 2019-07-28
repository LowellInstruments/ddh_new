import time


class ButtonPressEvent:
    def __init__(self, code):
        self.code = code

    def key(self):
        return self.code


class DeckDataHubGUI:

    # symbols = ('|', '/', '--', '\\', '|', '/', '--', '\\')
    symbols = ('.', '..', '...', ' ')
    indicator = ''
    index = 0

    @staticmethod
    def step_busy_indicator():
        DeckDataHubGUI.index += 1
        DeckDataHubGUI.index %= len(DeckDataHubGUI.symbols)
        return DeckDataHubGUI.symbols[DeckDataHubGUI.index]

    @staticmethod
    def gui_loop(signals):
        while 1:
            DeckDataHubGUI.indicator = DeckDataHubGUI.step_busy_indicator()
            signals.gui_tick.emit(DeckDataHubGUI.indicator)
            time.sleep(1)
