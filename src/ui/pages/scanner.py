from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QFont
from ..widgets.worker import Worker
from core.google_ip_scanner import scan_sync
from ..styles import COLORS

class ScannerPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_win = main_window
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()
        header = QLabel("IP Scanner")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['text_main']}; letter-spacing: -1px;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        self.scan_btn = QPushButton("Start Analysis")
        self.scan_btn.setObjectName("PrimaryAction")
        self.scan_btn.setMinimumWidth(160)
        self.scan_btn.clicked.connect(self._run_scan)
        header_layout.addWidget(self.scan_btn)
        layout.addLayout(header_layout)

        desc = QLabel("Find the fastest reachable Google frontend IP for your connection.")
        desc.setStyleSheet("color: #777; font-size: 14px;")
        layout.addWidget(desc)

        self.scanner_results = QTextEdit()
        self.scanner_results.setReadOnly(True)
        self.scanner_results.setObjectName("LogView")
        layout.addWidget(self.scanner_results)

    def _run_scan(self):
        self.scan_btn.setEnabled(False)
        self.scanner_results.clear()
        self.scanner_results.append("Starting IP scan... please wait...")

        self.thread = QThread()
        self.worker = Worker(scan_sync, self.main_win.config.get("front_domain", "www.google.com"))
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result.connect(self._on_scan_result)
        self.thread.start()

    def _on_scan_result(self, result):
        self.scan_btn.setEnabled(True)
        self.scanner_results.append("\nScan complete. Check the Logs tab for detailed results.")
