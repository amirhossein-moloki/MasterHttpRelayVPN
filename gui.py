import sys
import os
import json
import logging
import asyncio
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QListWidget, QListWidgetItem,
    QProgressBar, QTextEdit, QLineEdit, QFormLayout, QCheckBox,
    QFrame, QSizePolicy, QScrollArea, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize, QThread
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QTextCursor
import qtawesome as qta

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from core.proxy_service import ProxyService
from core.constants import __version__
from core.google_ip_scanner import scan_sync

# Setup Logging for UI
class QtLogHandler(logging.Handler, QObject):
    new_log = pyqtSignal(str, str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        msg = self.format(record)
        self.new_log.emit(msg, record.levelname)

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

class ModernUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"MasterHttpRelayVPN v{__version__}")
        self.setMinimumSize(900, 600)

        self.config_path = "config.json"
        self.config = self._load_config()
        self.proxy_service = ProxyService(self.config)
        self.proxy_service.status_changed.connect(self._on_proxy_status_change)

        self._init_ui()
        self._setup_logging()

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_stats)
        self.status_timer.start(1000)

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=2)

    def _setup_logging(self):
        self.log_handler = QtLogHandler()
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.log_handler.new_log.connect(self._append_log)
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)

    def _init_ui(self):
        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setStyleSheet("background-color: #2c3e50; color: white;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)

        logo_label = QLabel("MasterRelay")
        logo_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("margin-bottom: 20px;")
        sidebar_layout.addWidget(logo_label)

        self.nav_list = QListWidget()
        self.nav_list.setStyleSheet("""
            QListWidget { border: none; background-color: transparent; outline: none; }
            QListWidget::item { padding: 12px; border-radius: 5px; margin-bottom: 5px; color: #ecf0f1; }
            QListWidget::item:selected { background-color: #34495e; color: #3498db; font-weight: bold; }
            QListWidget::item:hover { background-color: #34495e; }
        """)

        items = [
            ("Dashboard", "fa.dashboard"),
            ("Settings", "fa.gears"),
            ("Logs", "fa.terminal"),
            ("IP Scanner", "fa.search"),
        ]

        for text, icon in items:
            item = QListWidgetItem(qta.icon(icon, color="white"), text)
            self.nav_list.addItem(item)

        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        sidebar_layout.addWidget(self.nav_list)

        sidebar_layout.addStretch()

        version_label = QLabel(f"v{__version__}")
        version_label.setStyleSheet("color: #95a5a6;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(self.sidebar)

        # Content Area
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #f5f6fa;")

        self.dashboard_page = self._create_dashboard_page()
        self.settings_page = self._create_settings_page()
        self.logs_page = self._create_logs_page()
        self.scanner_page = self._create_scanner_page()

        self.content_stack.addWidget(self.dashboard_page)
        self.content_stack.addWidget(self.settings_page)
        self.content_stack.addWidget(self.logs_page)
        self.content_stack.addWidget(self.scanner_page)

        main_layout.addWidget(self.content_stack)

    def _create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Dashboard")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(header)

        # Status Card
        status_card = QFrame()
        status_card.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #dcdde1;")
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(20, 20, 20, 20)

        self.status_icon = QLabel()
        self.status_icon.setPixmap(qta.icon("fa.circle", color="#7f8c8d").pixmap(48, 48))
        status_layout.addWidget(self.status_icon)

        status_text_layout = QVBoxLayout()
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        status_text_layout.addWidget(self.status_label)

        self.status_detail = QLabel("Ready to start")
        self.status_detail.setStyleSheet("color: #7f8c8d;")
        status_text_layout.addWidget(self.status_detail)
        status_layout.addLayout(status_text_layout)

        status_layout.addStretch()

        self.toggle_btn = QPushButton("Start Proxy")
        self.toggle_btn.setFixedSize(150, 40)
        self.toggle_btn.setStyleSheet("""
            QPushButton { background-color: #2ecc71; color: white; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.toggle_btn.clicked.connect(self._toggle_proxy)
        status_layout.addWidget(self.toggle_btn)

        layout.addWidget(status_card)

        # Quota Card
        quota_card = QFrame()
        quota_card.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #dcdde1;")
        quota_layout = QVBoxLayout(quota_card)
        quota_layout.setContentsMargins(20, 20, 20, 20)

        quota_header = QHBoxLayout()
        quota_title = QLabel("Daily Usage Quota")
        quota_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        quota_header.addWidget(quota_title)
        quota_header.addStretch()
        self.quota_label = QLabel("0 / 20000")
        quota_header.addWidget(self.quota_label)
        quota_layout.addLayout(quota_header)

        self.quota_progress = QProgressBar()
        self.quota_progress.setMaximum(20000)
        self.quota_progress.setValue(0)
        self.quota_progress.setTextVisible(False)
        self.quota_progress.setStyleSheet("""
            QProgressBar { height: 10px; border-radius: 5px; background-color: #f1f2f6; }
            QProgressBar::chunk { background-color: #3498db; border-radius: 5px; }
        """)
        quota_layout.addWidget(self.quota_progress)

        self.quota_hint = QLabel("Resets daily at 10:30 AM")
        self.quota_hint.setStyleSheet("color: #95a5a6; font-size: 10px;")
        quota_layout.addWidget(self.quota_hint)

        layout.addWidget(quota_card)

        # Stats Area
        stats_layout = QHBoxLayout()

        def create_stat_box(title, value):
            box = QFrame()
            box.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #dcdde1;")
            blayout = QVBoxLayout(box)
            tlabel = QLabel(title)
            tlabel.setStyleSheet("color: #7f8c8d; font-size: 12px;")
            vlabel = QLabel(value)
            vlabel.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            blayout.addWidget(tlabel)
            blayout.addWidget(vlabel)
            return box, vlabel

        self.stat_box_1, self.val_requests = create_stat_box("Total Requests", "0")
        self.stat_box_2, self.val_data = create_stat_box("Data Transferred", "0 MB")
        self.stat_box_3, self.val_latency = create_stat_box("Avg Latency", "0 ms")

        stats_layout.addWidget(self.stat_box_1)
        stats_layout.addWidget(self.stat_box_2)
        stats_layout.addWidget(self.stat_box_3)
        layout.addLayout(stats_layout)

        layout.addStretch()
        return page

    def _create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Settings")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        form_layout = QFormLayout(scroll_content)
        form_layout.setSpacing(15)

        # Config Fields
        self.edit_script_id = QLineEdit(self.config.get("script_id", ""))
        self.edit_script_id.setPlaceholderText("Apps Script Deployment ID")
        form_layout.addRow("Deployment ID:", self.edit_script_id)

        self.edit_auth_key = QLineEdit(self.config.get("auth_key", ""))
        self.edit_auth_key.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Auth Key:", self.edit_auth_key)

        self.edit_google_ip = QLineEdit(self.config.get("google_ip", "216.239.38.120"))
        form_layout.addRow("Google IP:", self.edit_google_ip)

        self.edit_listen_port = QLineEdit(str(self.config.get("listen_port", 8085)))
        form_layout.addRow("HTTP Port:", self.edit_listen_port)

        self.edit_socks_port = QLineEdit(str(self.config.get("socks5_port", 1080)))
        form_layout.addRow("SOCKS5 Port:", self.edit_socks_port)

        self.check_lan = QCheckBox("Enable LAN Sharing")
        self.check_lan.setChecked(self.config.get("lan_sharing", False))
        form_layout.addRow("", self.check_lan)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        btn_save = QPushButton("Save Settings")
        btn_save.setFixedSize(150, 40)
        btn_save.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; font-weight: bold;")
        btn_save.clicked.connect(self._save_settings_from_ui)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignRight)

        return page

    def _create_logs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QHBoxLayout()
        header_text = QLabel("System Logs")
        header_text.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.addWidget(header_text)
        header.addStretch()

        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(lambda: self.log_view.clear())
        header.addWidget(btn_clear)
        layout.addLayout(header)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            QTextEdit { background-color: #1e272e; color: #dcdde1; font-family: 'Consolas', monospace; font-size: 11px; border-radius: 5px; }
        """)
        layout.addWidget(self.log_view)

        return page

    def _create_scanner_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Google IP Scanner")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        layout.addWidget(header)

        desc = QLabel("Find the fastest reachable Google frontend IP for your connection.")
        desc.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(desc)

        self.scanner_results = QTextEdit()
        self.scanner_results.setReadOnly(True)
        self.scanner_results.setStyleSheet("background-color: white; border: 1px solid #dcdde1; border-radius: 5px;")
        layout.addWidget(self.scanner_results)

        self.scan_btn = QPushButton("Start Scan")
        self.scan_btn.setFixedSize(150, 40)
        self.scan_btn.setStyleSheet("background-color: #9b59b6; color: white; border-radius: 5px; font-weight: bold;")
        self.scan_btn.clicked.connect(self._run_scan)
        layout.addWidget(self.scan_btn, alignment=Qt.AlignmentFlag.AlignRight)

        return page

    # Handlers
    def _on_nav_changed(self, index):
        self.content_stack.setCurrentIndex(index)

    def _toggle_proxy(self):
        if self.proxy_service.is_running:
            self.proxy_service.stop()
        else:
            self._save_settings_from_ui()
            self.proxy_service.config = self.config
            self.proxy_service.start()

    def _on_proxy_status_change(self, status):
        if status == "starting":
            self.status_label.setText("Status: Starting...")
            self.status_icon.setPixmap(qta.icon("fa.circle", color="#f1c40f").pixmap(48, 48))
            self.toggle_btn.setEnabled(False)
        elif status == "stopped":
            self.status_label.setText("Status: Disconnected")
            self.status_icon.setPixmap(qta.icon("fa.circle", color="#7f8c8d").pixmap(48, 48))
            self.toggle_btn.setText("Start Proxy")
            self.toggle_btn.setStyleSheet("background-color: #2ecc71; color: white; border-radius: 5px; font-weight: bold;")
            self.toggle_btn.setEnabled(True)
            self.status_detail.setText("Ready to start")
        elif "error" in status:
            self.status_label.setText("Status: Error")
            self.status_icon.setPixmap(qta.icon("fa.circle", color="#e74c3c").pixmap(48, 48))
            self.status_detail.setText(status)
            self.toggle_btn.setText("Start Proxy")
            self.toggle_btn.setEnabled(True)
        else:
            # Running
            self.status_label.setText("Status: Connected")
            self.status_icon.setPixmap(qta.icon("fa.circle", color="#2ecc71").pixmap(48, 48))
            self.toggle_btn.setText("Stop Proxy")
            self.toggle_btn.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 5px; font-weight: bold;")
            self.toggle_btn.setEnabled(True)
            self.status_detail.setText(f"Listening on {self.config.get('listen_host')}:{self.config.get('listen_port')}")

    def _update_stats(self):
        usage = self.proxy_service.get_usage()
        if usage:
            self.quota_label.setText(f"{usage['count']} / {usage['limit']}")
            self.quota_progress.setValue(usage['count'])
            if usage['percent'] > 90:
                self.quota_progress.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
            elif usage['percent'] > 70:
                self.quota_progress.setStyleSheet("QProgressBar::chunk { background-color: #f1c40f; }")
            else:
                self.quota_progress.setStyleSheet("QProgressBar::chunk { background-color: #3498db; }")

        stats = self.proxy_service.get_stats()
        if stats:
            total_req = sum(s['requests'] for s in stats['per_site'])
            total_bytes = sum(s['bytes'] for s in stats['per_site'])
            avg_latency = 0
            if total_req > 0:
                avg_latency = sum(s['avg_ms'] * s['requests'] for s in stats['per_site']) / total_req

            self.val_requests.setText(str(total_req))
            self.val_data.setText(f"{total_bytes / (1024*1024):.1f} MB")
            self.val_latency.setText(f"{avg_latency:.0f} ms")

    def _append_log(self, msg, level):
        color = "#dcdde1"
        if level == "WARNING": color = "#f1c40f"
        elif level == "ERROR": color = "#e74c3c"
        elif level == "DEBUG": color = "#7f8c8d"

        self.log_view.append(f'<span style="color: {color};">{msg}</span>')
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _save_settings_from_ui(self):
        self.config["script_id"] = self.edit_script_id.text()
        self.config["auth_key"] = self.edit_auth_key.text()
        self.config["google_ip"] = self.edit_google_ip.text()
        try:
            self.config["listen_port"] = int(self.edit_listen_port.text())
            self.config["socks5_port"] = int(self.edit_socks_port.text())
        except:
            pass
        self.config["lan_sharing"] = self.check_lan.isChecked()
        self.config["mode"] = "apps_script"
        self._save_config()

    def _run_scan(self):
        self.scan_btn.setEnabled(False)
        self.scanner_results.clear()
        self.scanner_results.append("Starting IP scan... please wait...")

        self.thread = QThread()
        self.worker = Worker(scan_sync, self.config.get("front_domain", "www.google.com"))
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.result.connect(self._on_scan_result)
        self.thread.start()

    def _on_scan_result(self, result):
        self.scan_btn.setEnabled(True)
        # Capture stdout from scan_sync might be tricky, but we can at least show it finished.
        self.scanner_results.append("\nScan complete. Check the Logs tab for detailed results.")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark mode-ish palette for Fusion
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(245, 246, 250))
    app.setPalette(palette)

    window = ModernUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
