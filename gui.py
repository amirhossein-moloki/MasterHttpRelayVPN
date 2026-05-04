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
    QFrame, QSizePolicy, QScrollArea, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize, QThread
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QTextCursor
import qtawesome as qta

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from core.proxy_service import ProxyService
from core.constants import __version__
from datetime import datetime, timedelta
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
        self.sidebar.setStyleSheet("background-color: #1a1a1a; color: white; border-right: 1px solid #333;")
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
            QListWidget::item { padding: 12px; border-radius: 5px; margin-bottom: 5px; color: #b0b0b0; }
            QListWidget::item:selected { background-color: #333333; color: #3498db; font-weight: bold; }
            QListWidget::item:hover { background-color: #252525; }
        """)

        items = [
            ("Dashboard", "fa5s.tachometer-alt"),
            ("Monitoring", "fa5s.chart-bar"),
            ("Settings", "fa5s.sliders-h"),
            ("Logs", "fa5s.terminal"),
            ("IP Scanner", "fa5s.search"),
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
        self.content_stack.setStyleSheet("background-color: #121212; color: #e0e0e0;")

        self.dashboard_page = self._create_dashboard_page()
        self.monitoring_page = self._create_monitoring_page()
        self.settings_page = self._create_settings_page()
        self.logs_page = self._create_logs_page()
        self.scanner_page = self._create_scanner_page()

        self.content_stack.addWidget(self.dashboard_page)
        self.content_stack.addWidget(self.monitoring_page)
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
        header.setStyleSheet("color: white;")
        layout.addWidget(header)

        # Status Card
        status_card = QFrame()
        status_card.setStyleSheet("background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333;")
        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(20, 20, 20, 20)

        self.status_icon = QLabel()
        self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#7f8c8d").pixmap(48, 48))
        status_layout.addWidget(self.status_icon)

        status_text_layout = QVBoxLayout()
        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        status_text_layout.addWidget(self.status_label)

        self.status_detail = QLabel("Ready to start")
        self.status_detail.setStyleSheet("color: #b0b0b0;")
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
        quota_card.setStyleSheet("background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333;")
        quota_layout = QVBoxLayout(quota_card)
        quota_layout.setContentsMargins(20, 20, 20, 20)

        quota_header = QHBoxLayout()
        quota_title = QLabel("Daily Usage Quota")
        quota_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        quota_header.addWidget(quota_title)
        quota_header.addStretch()

        script_ids = self.config.get("script_ids") or self.config.get("script_id")
        num_scripts = len(script_ids) if isinstance(script_ids, list) else (1 if script_ids else 0)
        initial_limit = 20000 * num_scripts if num_scripts > 0 else 20000

        self.quota_label = QLabel(f"0 / {initial_limit}")
        quota_header.addWidget(self.quota_label)
        quota_layout.addLayout(quota_header)

        self.quota_progress = QProgressBar()
        self.quota_progress.setMaximum(initial_limit)
        self.quota_progress.setValue(0)
        self.quota_progress.setTextVisible(False)
        self.quota_progress.setStyleSheet("""
            QProgressBar { height: 10px; border-radius: 5px; background-color: #333333; }
            QProgressBar::chunk { background-color: #3498db; border-radius: 5px; }
        """)
        quota_layout.addWidget(self.quota_progress)

        self.quota_hint = QLabel("Resets daily at 10:30 AM")
        self.quota_hint.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        quota_layout.addWidget(self.quota_hint)

        layout.addWidget(quota_card)

        # Stats Area
        stats_layout = QHBoxLayout()

        def create_stat_box(title, value):
            box = QFrame()
            box.setStyleSheet("background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333;")
            blayout = QVBoxLayout(box)
            tlabel = QLabel(title)
            tlabel.setStyleSheet("color: #b0b0b0; font-size: 12px;")
            vlabel = QLabel(value)
            vlabel.setFont(QFont("Arial", 18, QFont.Weight.Bold))
            vlabel.setStyleSheet("color: white;")
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

    def _create_monitoring_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Usage Monitoring")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)

        # Summary Stats
        stats_layout = QHBoxLayout()
        def create_mon_box(title):
            box = QFrame()
            box.setStyleSheet("background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333;")
            blayout = QVBoxLayout(box)
            tlabel = QLabel(title)
            tlabel.setStyleSheet("color: #b0b0b0; font-size: 12px;")
            vlabel = QLabel("0")
            vlabel.setFont(QFont("Arial", 16, QFont.Weight.Bold))
            vlabel.setStyleSheet("color: white;")
            blayout.addWidget(tlabel)
            blayout.addWidget(vlabel)
            return box, vlabel

        self.mon_total_req, self.mon_val_req = create_mon_box("Total Requests")
        self.mon_total_up, self.mon_val_up = create_mon_box("Total Upload")
        self.mon_total_down, self.mon_val_down = create_mon_box("Total Download")

        stats_layout.addWidget(self.mon_total_req)
        stats_layout.addWidget(self.mon_total_up)
        stats_layout.addWidget(self.mon_total_down)
        layout.addLayout(stats_layout)

        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Time Filter:"))
        from PyQt6.QtWidgets import QComboBox
        self.time_filter = QComboBox()
        self.time_filter.addItems(["Daily", "Weekly", "Monthly"])
        self.time_filter.setStyleSheet("background-color: #333; color: white; padding: 5px; border-radius: 5px;")
        self.time_filter.currentIndexChanged.connect(self._update_stats)
        filter_layout.addWidget(self.time_filter)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Chart
        from core.chart_widget import SimpleChart
        self.usage_chart = SimpleChart()
        layout.addWidget(self.usage_chart)

        # Top 10 Table
        top_header = QLabel("Top 10 Most Used Domains")
        top_header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        top_header.setStyleSheet("margin-top: 20px; color: #3498db;")
        layout.addWidget(top_header)

        self.top_table = QTableWidget(0, 4)
        self.top_table.setHorizontalHeaderLabels(["Domain", "Requests", "Upload", "Download"])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.top_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
                gridline-color: #333;
                border: 1px solid #333;
                border-radius: 5px;
            }
            QHeaderView::section {
                background-color: #252525;
                color: #b0b0b0;
                padding: 5px;
                border: none;
            }
        """)
        layout.addWidget(self.top_table)

        layout.addStretch()
        return page

    def _create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QLabel("Professional Settings")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)

        self.settings_tabs = QTabWidget()
        self.settings_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333; background: #121212; border-radius: 5px; }
            QTabBar::tab { background: #1a1a1a; color: #b0b0b0; padding: 10px 20px; border-top-left-radius: 5px; border-top-right-radius: 5px; }
            QTabBar::tab:selected { background: #333; color: #3498db; }
        """)

        # Tab 1: Network
        net_tab = QWidget()
        net_layout = QFormLayout(net_tab)
        net_layout.setContentsMargins(20, 20, 20, 20)
        net_layout.setSpacing(15)

        input_style = """
            QLineEdit { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #333; padding: 8px; border-radius: 5px; }
            QCheckBox { color: #e0e0e0; }
        """
        label_style = "color: #b0b0b0;"

        def add_row(lay, label, widget):
            lbl = QLabel(label)
            lbl.setStyleSheet(label_style)
            lay.addRow(lbl, widget)

        self.edit_script_id = QLineEdit(self.config.get("script_id", ""))
        self.edit_script_id.setStyleSheet(input_style)
        add_row(net_layout, "Deployment ID:", self.edit_script_id)

        self.edit_auth_key = QLineEdit(self.config.get("auth_key", ""))
        self.edit_auth_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_auth_key.setStyleSheet(input_style)
        add_row(net_layout, "Auth Key:", self.edit_auth_key)

        self.edit_google_ip = QLineEdit(self.config.get("google_ip", "216.239.38.120"))
        self.edit_google_ip.setStyleSheet(input_style)
        add_row(net_layout, "Google IP:", self.edit_google_ip)

        self.edit_listen_port = QLineEdit(str(self.config.get("listen_port", 8085)))
        self.edit_listen_port.setStyleSheet(input_style)
        add_row(net_layout, "HTTP Port:", self.edit_listen_port)

        self.edit_socks_port = QLineEdit(str(self.config.get("socks5_port", 1080)))
        self.edit_socks_port.setStyleSheet(input_style)
        add_row(net_layout, "SOCKS5 Port:", self.edit_socks_port)

        self.check_lan = QCheckBox("Enable LAN Sharing")
        self.check_lan.setChecked(self.config.get("lan_sharing", False))
        self.check_lan.setStyleSheet(input_style)
        add_row(net_layout, "", self.check_lan)

        # Tab 2: Bypass
        bypass_tab = QWidget()
        bypass_layout = QVBoxLayout(bypass_tab)
        bypass_layout.setContentsMargins(20, 20, 20, 20)

        self.check_iran_ips = QCheckBox("Automatically bypass all Iran IP ranges (GeoIP)")
        self.check_iran_ips.setChecked(self.config.get("bypass_iran_ips", True))
        self.check_iran_ips.setStyleSheet(input_style)
        bypass_layout.addWidget(self.check_iran_ips)

        bypass_layout.addWidget(QLabel("Manual Bypass Hosts (one per line, e.g. example.ir or .local):"))
        self.edit_bypass_hosts = QTextEdit()
        self.edit_bypass_hosts.setPlainText("\n".join(self.config.get("bypass_hosts", [])))
        self.edit_bypass_hosts.setStyleSheet("background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #333; border-radius: 5px;")
        bypass_layout.addWidget(self.edit_bypass_hosts)

        bypass_layout.addWidget(QLabel("Manual Bypass IPs/CIDR (one per line, e.g. 1.2.3.4 or 192.168.1.0/24):"))
        self.edit_manual_ips = QTextEdit()
        self.edit_manual_ips.setPlainText("\n".join(self.config.get("manual_bypass_ips", [])))
        self.edit_manual_ips.setStyleSheet("background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #333; border-radius: 5px;")
        bypass_layout.addWidget(self.edit_manual_ips)

        # Tab 3: Presets
        presets_tab = QWidget()
        presets_layout = QVBoxLayout(presets_tab)
        presets_layout.setContentsMargins(20, 20, 20, 20)

        presets_layout.addWidget(QLabel("Manage Configuration Presets:"))

        self.presets_list = QListWidget()
        self.presets_list.setStyleSheet("background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #333; border-radius: 5px;")
        presets_layout.addWidget(self.presets_list)

        pres_btn_layout = QHBoxLayout()
        btn_save_preset = QPushButton("Save Current as Preset")
        btn_save_preset.clicked.connect(self._save_preset)
        btn_load_preset = QPushButton("Load Selected Preset")
        btn_load_preset.clicked.connect(self._load_preset)
        btn_delete_preset = QPushButton("Delete Preset")
        btn_delete_preset.clicked.connect(self._delete_preset)

        for b in [btn_save_preset, btn_load_preset, btn_delete_preset]:
            b.setStyleSheet("background-color: #333; color: white; padding: 8px; border-radius: 5px;")
            pres_btn_layout.addWidget(b)

        presets_layout.addLayout(pres_btn_layout)
        self._refresh_presets()

        self.settings_tabs.addTab(net_tab, "Network")
        self.settings_tabs.addTab(bypass_tab, "Bypass")
        self.settings_tabs.addTab(presets_tab, "Presets")

        layout.addWidget(self.settings_tabs)

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
        header_text.setStyleSheet("color: white;")
        header.addWidget(header_text)
        header.addStretch()

        btn_clear = QPushButton("Clear")
        btn_clear.setStyleSheet("""
            QPushButton { background-color: #333; color: white; border-radius: 5px; padding: 5px 15px; }
            QPushButton:hover { background-color: #444; }
        """)
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
        header.setStyleSheet("color: white;")
        layout.addWidget(header)

        desc = QLabel("Find the fastest reachable Google frontend IP for your connection.")
        desc.setStyleSheet("color: #b0b0b0;")
        layout.addWidget(desc)

        self.scanner_results = QTextEdit()
        self.scanner_results.setReadOnly(True)
        self.scanner_results.setStyleSheet("""
            QTextEdit { background-color: #1e272e; color: #dcdde1; font-family: 'Consolas', monospace; border-radius: 5px; border: 1px solid #333; }
        """)
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
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#f1c40f").pixmap(48, 48))
            self.toggle_btn.setEnabled(False)
        elif status == "stopped":
            self.status_label.setText("Status: Disconnected")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#7f8c8d").pixmap(48, 48))
            self.toggle_btn.setText("Start Proxy")
            self.toggle_btn.setStyleSheet("background-color: #2ecc71; color: white; border-radius: 5px; font-weight: bold;")
            self.toggle_btn.setEnabled(True)
            self.status_detail.setText("Ready to start")
        elif "error" in status:
            self.status_label.setText("Status: Error")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#e74c3c").pixmap(48, 48))
            self.status_detail.setText(status)
            self.toggle_btn.setText("Start Proxy")
            self.toggle_btn.setEnabled(True)
        else:
            # Running
            self.status_label.setText("Status: Connected")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#2ecc71").pixmap(48, 48))
            self.toggle_btn.setText("Stop Proxy")
            self.toggle_btn.setStyleSheet("background-color: #e74c3c; color: white; border-radius: 5px; font-weight: bold;")
            self.toggle_btn.setEnabled(True)
            self.status_detail.setText(f"Listening on {self.config.get('listen_host')}:{self.config.get('listen_port')}")

    def _update_stats(self):
        usage = self.proxy_service.get_usage()
        if usage:
            self.quota_label.setText(f"{usage['count']} / {usage['limit']}")
            self.quota_progress.setMaximum(usage['limit'])
            self.quota_progress.setValue(usage['count'])
            if usage['percent'] > 90:
                self.quota_progress.setStyleSheet("QProgressBar { background-color: #333; } QProgressBar::chunk { background-color: #e74c3c; }")
            elif usage['percent'] > 70:
                self.quota_progress.setStyleSheet("QProgressBar { background-color: #333; } QProgressBar::chunk { background-color: #f1c40f; }")
            else:
                self.quota_progress.setStyleSheet("QProgressBar { background-color: #333; } QProgressBar::chunk { background-color: #3498db; }")

        detailed_stats = self.proxy_service.get_detailed_stats()
        if detailed_stats:
            filter_mode = self.time_filter.currentText()
            days = 1 if filter_mode == "Daily" else (7 if filter_mode == "Weekly" else 30)

            total_req = 0
            total_up = 0
            total_down = 0
            all_hosts = {}

            chart_data = []

            for i in range(days):
                d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                d_data = detailed_stats.get(d, {"total_requests": 0, "total_upload": 0, "total_download": 0, "hosts": {}})
                total_req += d_data["total_requests"]
                total_up += d_data["total_upload"]
                total_down += d_data["total_download"]

                chart_data.insert(0, (d[-2:], (d_data["total_upload"] + d_data["total_download"]) / (1024*1024)))

                for h, hdata in d_data["hosts"].items():
                    if h not in all_hosts:
                        all_hosts[h] = {"requests": 0, "upload": 0, "download": 0}
                    all_hosts[h]["requests"] += hdata["requests"]
                    all_hosts[h]["upload"] += hdata["upload"]
                    all_hosts[h]["download"] += hdata["download"]

            # Update Dashboard (Today only for dashboard)
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_data = detailed_stats.get(today_str, {"total_requests": 0, "total_upload": 0, "total_download": 0})
            self.val_requests.setText(str(today_data["total_requests"]))
            self.val_data.setText(f"{(today_data['total_upload'] + today_data['total_download']) / (1024*1024):.1f} MB")

            # Update Monitoring page
            self.mon_val_req.setText(str(total_req))
            self.mon_val_up.setText(f"{total_up / (1024*1024):.2f} MB")
            self.mon_val_down.setText(f"{total_down / (1024*1024):.2f} MB")

            self.usage_chart.set_data(chart_data)

            # Update Top 10 Table
            sorted_hosts = sorted(all_hosts.items(), key=lambda x: x[1]['download'] + x[1]['upload'], reverse=True)[:10]

            # Only update if data changed to avoid flicker
            current_top = getattr(self, "_last_top_10", [])
            if sorted_hosts != current_top:
                self.top_table.setRowCount(len(sorted_hosts))
                for i, (host, hdata) in enumerate(sorted_hosts):
                    self.top_table.setItem(i, 0, QTableWidgetItem(host))
                    self.top_table.setItem(i, 1, QTableWidgetItem(str(hdata['requests'])))
                    self.top_table.setItem(i, 2, QTableWidgetItem(f"{hdata['upload'] / 1024:.1f} KB"))
                    self.top_table.setItem(i, 3, QTableWidgetItem(f"{hdata['download'] / 1024:.1f} KB"))
                self._last_top_10 = sorted_hosts

        stats = self.proxy_service.get_stats()
        if stats:
            total_req = sum(s['requests'] for s in stats['per_site'])
            avg_latency = 0
            if total_req > 0:
                avg_latency = sum(s['avg_ms'] * s['requests'] for s in stats['per_site']) / total_req
            self.val_latency.setText(f"{avg_latency:.0f} ms")

    def _append_log(self, msg, level):
        color = "#dcdde1"
        if level == "WARNING": color = "#f1c40f"
        elif level == "ERROR": color = "#e74c3c"
        elif level == "DEBUG": color = "#7f8c8d"

        self.log_view.append(f'<span style="color: {color};">{msg}</span>')
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    def _refresh_presets(self):
        self.presets_list.clear()
        if os.path.exists("presets"):
            for f in os.listdir("presets"):
                if f.endswith(".json"):
                    self.presets_list.addItem(f[:-5])

    def _save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset Name:")
        if ok and name:
            self._save_settings_from_ui()
            with open(f"presets/{name}.json", "w") as f:
                json.dump(self.config, f, indent=2)
            self._refresh_presets()

    def _load_preset(self):
        item = self.presets_list.currentItem()
        if item:
            name = item.text()
            with open(f"presets/{name}.json", "r") as f:
                self.config = json.load(f)
            self._update_ui_from_config()
            QMessageBox.information(self, "Success", f"Preset '{name}' loaded successfully.")

    def _delete_preset(self):
        item = self.presets_list.currentItem()
        if item:
            name = item.text()
            os.remove(f"presets/{name}.json")
            self._refresh_presets()

    def _update_ui_from_config(self):
        self.edit_script_id.setText(self.config.get("script_id", ""))
        self.edit_auth_key.setText(self.config.get("auth_key", ""))
        self.edit_google_ip.setText(self.config.get("google_ip", "216.239.38.120"))
        self.edit_listen_port.setText(str(self.config.get("listen_port", 8085)))
        self.edit_socks_port.setText(str(self.config.get("socks5_port", 1080)))
        self.check_lan.setChecked(self.config.get("lan_sharing", False))
        self.check_iran_ips.setChecked(self.config.get("bypass_iran_ips", True))
        self.edit_bypass_hosts.setPlainText("\n".join(self.config.get("bypass_hosts", [])))
        self.edit_manual_ips.setPlainText("\n".join(self.config.get("manual_bypass_ips", [])))

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
        self.config["bypass_iran_ips"] = self.check_iran_ips.isChecked()

        bypass_text = self.edit_bypass_hosts.toPlainText()
        self.config["bypass_hosts"] = [h.strip() for h in bypass_text.split("\n") if h.strip()]

        manual_ips_text = self.edit_manual_ips.toPlainText()
        self.config["manual_bypass_ips"] = [h.strip() for h in manual_ips_text.split("\n") if h.strip()]

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
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(18, 18, 18))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(18, 18, 18))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(dark_palette)

    window = ModernUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
