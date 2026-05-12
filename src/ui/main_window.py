import sys
import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QListWidget, QListWidgetItem,
    QSizePolicy, QFileDialog, QMessageBox, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor
import qtawesome as qta

# Internal imports
from .styles import STYLE_SHEET, COLORS
from .widgets.log_handler import QtLogHandler
from services.proxy_service import ProxyService
from core.constants import __version__

# Pages (We will define them in a moment)
from .pages.dashboard import DashboardPage
from .pages.monitoring import MonitoringPage
from .pages.routing import RoutingPage
from .pages.settings import SettingsPage
from .pages.logs import LogsPage
from .pages.scanner import ScannerPage
from .pages.sni_tester import SNITesterPage

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

class ModernUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"MasterHttpRelayVPN v{__version__}")
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(STYLE_SHEET)

        # Set Window Icon
        icon_path = resource_path("assets/icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.config_path = "config.json"
        self.config = self._load_config()
        self.proxy_service = ProxyService(self.config)
        self.proxy_service.status_changed.connect(self._on_proxy_status_change)

        self._setup_logging()
        self._init_ui()

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
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 32, 0, 16)
        sidebar_layout.setSpacing(8)

        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(24, 0, 24, 24)

        logo_icon = QLabel()
        logo_icon.setPixmap(qta.icon("fa5s.shield-alt", color=COLORS['primary']).pixmap(28, 28))
        logo_layout.addWidget(logo_icon)

        logo_label = QLabel("MasterRelay")
        logo_label.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        logo_label.setStyleSheet(f"color: {COLORS['text_main']}; letter-spacing: -0.5px;")
        logo_layout.addWidget(logo_label)
        logo_layout.addStretch()
        sidebar_layout.addWidget(logo_container)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList")

        items = [
            ("Dashboard", "fa5s.th-large"),
            ("Monitoring", "fa5s.chart-line"),
            ("Routing Rules", "fa5s.directions"),
            ("Settings", "fa5s.sliders-h"),
            ("Logs", "fa5s.terminal"),
            ("IP Scanner", "fa5s.microscope"),
            ("SNI Tester", "fa5s.vial"),
        ]

        for text, icon in items:
            item = QListWidgetItem(qta.icon(icon, color=COLORS['text_secondary']), text)
            self.nav_list.addItem(item)

        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sidebar_layout.addWidget(self.nav_list)

        version_label = QLabel(f"v{__version__}")
        version_label.setStyleSheet("color: #95a5a6;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version_label)

        main_layout.addWidget(self.sidebar)

        # Content Area
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentStack")

        self.dashboard_page = DashboardPage(self)
        self.monitoring_page = MonitoringPage(self)
        self.routing_page = RoutingPage(self)
        self.settings_page = SettingsPage(self)
        self.logs_page = LogsPage(self)
        self.scanner_page = ScannerPage(self)
        self.sni_tester_page = SNITesterPage(self)

        self.content_stack.addWidget(self.dashboard_page)
        self.content_stack.addWidget(self.monitoring_page)
        self.content_stack.addWidget(self.routing_page)
        self.content_stack.addWidget(self.settings_page)
        self.content_stack.addWidget(self.logs_page)
        self.content_stack.addWidget(self.scanner_page)
        self.content_stack.addWidget(self.sni_tester_page)

        main_layout.addWidget(self.content_stack)

    def _on_nav_changed(self, index):
        # Stop existing animation if running
        if hasattr(self, "_nav_anim") and self._nav_anim.state() == QPropertyAnimation.State.Running:
            self._nav_anim.stop()

        target_widget = self.content_stack.widget(index)
        if not target_widget:
            return

        # Create effect for the target widget
        eff = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(eff)

        self._nav_anim = QPropertyAnimation(eff, b"opacity")
        self._nav_anim.setDuration(250)
        self._nav_anim.setStartValue(0.0)
        self._nav_anim.setEndValue(1.0)
        self._nav_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Change page
        self.content_stack.setCurrentIndex(index)

        # Clean up effect after animation
        self._nav_anim.finished.connect(lambda: target_widget.setGraphicsEffect(None))
        self._nav_anim.start()

    def _on_proxy_status_change(self, status):
        self.dashboard_page.update_status(status)

    def _update_stats(self):
        self.dashboard_page.refresh_stats()
        if self.content_stack.currentWidget() == self.monitoring_page:
            self.monitoring_page.refresh_stats()

    def closeEvent(self, event):
        if self.proxy_service.is_running:
            logging.info("Closing window, stopping proxy...")
            self.proxy_service.stop()
        event.accept()
