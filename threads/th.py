from PyQt5.QtCore import QRunnable


class DDHThread(QRunnable):
    def __init__(self, fxn, sig, *args, **kwargs):
        super(DDHThread, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.sig = sig()
        self.fxn = fxn

    def run(self):
        self.fxn(self.sig, *self.args)

    def signals(self):
        return self.sig
