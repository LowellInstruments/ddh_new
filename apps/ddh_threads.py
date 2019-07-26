import traceback
import sys
from PyQt5.QtCore import QRunnable


class DDHThread(QRunnable):
    def __init__(self, fn, signals, *args, **kwargs):
        super(DDHThread, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = signals()

    def run(self):
        try:
            self.fn(self.signals, *self.args, **self.kwargs)
        except (ValueError, TypeError):
            self.signals.error.emit(traceback.print_exc())
            sys.exit('Error creating threads')
