from PyQt6.QtCore import QObject, pyqtSignal

class Worker(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        res = self.fn(*self.args, **self.kwargs)
        self.result.emit(res)
        self.finished.emit()
