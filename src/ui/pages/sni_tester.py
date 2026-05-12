import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFormLayout
)
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QFont
from ..widgets.worker import Worker
from core.sni_tester import test_sni
from ..styles import COLORS

class SNITesterPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_win = main_window
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()
        header = QLabel("SNI Tester")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['text_main']}; letter-spacing: -1px;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        self.test_btn = QPushButton("Run Test")
        self.test_btn.setObjectName("PrimaryAction")
        self.test_btn.setMinimumWidth(160)
        self.test_btn.clicked.connect(self._run_test)
        header_layout.addWidget(self.test_btn)
        layout.addLayout(header_layout)

        desc = QLabel("Verify if a domain's SNI is blocked or reachable through the configured Google IP.")
        desc.setStyleSheet("color: #777; font-size: 14px;")
        layout.addWidget(desc)

        form = QFormLayout()
        self.edit_domain = QLineEdit()
        self.edit_domain.setPlaceholderText("e.g., www.youtube.com")
        self.edit_domain.setText("www.youtube.com")
        form.addRow(QLabel("Domain to Test:"), self.edit_domain)

        self.edit_ip = QLineEdit()
        current_ip = self.main_win.config.get("google_ip", "216.239.38.120")
        self.edit_ip.setPlaceholderText("e.g., 216.239.38.120")
        self.edit_ip.setText(current_ip)
        form.addRow(QLabel("Target IP:"), self.edit_ip)

        layout.addLayout(form)

        self.results_view = QTextEdit()
        self.results_view.setReadOnly(True)
        self.results_view.setObjectName("LogView")
        layout.addWidget(self.results_view)

    def _run_test(self):
        domain = self.edit_domain.text().strip()
        ip = self.edit_ip.text().strip()
        if not domain or not ip:
            return

        self.test_btn.setEnabled(False)
        self.results_view.clear()
        self.results_view.append(f"Testing {domain} via {ip}...")

        def run_test_sync(domain, ip):
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(test_sni(domain, ip))
            except Exception as e:
                return str(e)

        self.thread = QThread()
        self.worker = Worker(run_test_sync, domain, ip)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result.connect(self._on_test_result)
        self.thread.start()

    def _on_test_result(self, result):
        self.test_btn.setEnabled(True)
        if isinstance(result, str):
            self.results_view.append(f"\nError: {result}")
            return

        if result.ok:
            self.results_view.append(f"\nSUCCESS!")
            self.results_view.append(f"Latency: {result.latency_ms}ms")
            self.results_view.append(f"Status Code: {result.status_code}")
            if result.status_code and result.status_code >= 400:
                self.results_view.append("\nNote: The domain is reachable, but the server returned an error. This is often normal for SNI fronting if the domain isn't fully supported by that specific edge IP.")
        else:
            self.results_view.append(f"\nFAILED!")
            self.results_view.append(f"Error: {result.error}")
            self.results_view.append("\nThis SNI appears to be blocked or the target IP is unreachable.")
