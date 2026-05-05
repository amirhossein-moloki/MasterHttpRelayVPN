import logging
from PyQt6.QtCore import QObject, pyqtSignal

class QtLogHandler(logging.Handler, QObject):
    new_log = pyqtSignal(str, str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.new_log.emit(msg, record.levelname)
