from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor
from ..styles import COLORS

class LogsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_win = main_window
        self._init_ui()
        self.main_win.log_handler.new_log.connect(self._append_log)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header = QHBoxLayout()
        header_text = QLabel("System Logs")
        header_text.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header_text.setStyleSheet(f"color: {COLORS['text_main']}; letter-spacing: -1px;")
        header.addWidget(header_text)
        header.addStretch()

        btn_clear = QPushButton("Clear Logs")
        btn_clear.setObjectName("SecondaryAction")
        btn_clear.clicked.connect(lambda: self.log_view.clear())
        header.addWidget(btn_clear)
        layout.addLayout(header)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setObjectName("LogView")
        layout.addWidget(self.log_view)

    def _append_log(self, msg, level):
        color = "#dcdde1"
        if level == "WARNING": color = "#f1c40f"
        elif level == "ERROR": color = "#e74c3c"
        elif level == "DEBUG": color = "#7f8c8d"

        self.log_view.append(f'<span style="color: {color};">{msg}</span>')
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)
