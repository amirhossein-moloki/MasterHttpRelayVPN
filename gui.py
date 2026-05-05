import sys
import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QListWidget, QListWidgetItem,
    QProgressBar, QTextEdit, QLineEdit, QFormLayout, QCheckBox,
    QFrame, QSizePolicy, QScrollArea, QFileDialog, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QSpinBox,
    QInputDialog, QMessageBox, QDialog, QDialogButtonBox, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize, QThread, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QTextCursor, QPainter, QPen, QBrush
import qtawesome as qta

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

from core.proxy_service import ProxyService
from core.constants import __version__
from core.google_ip_scanner import scan_sync

# Design Constants
STYLE_SHEET = """
    QMainWindow { background-color: #0A0A0A; }
    QWidget { font-family: 'Inter', 'Segoe UI', 'Roboto', 'Arial'; }

    /* Sidebar */
    #Sidebar { background-color: #111111; border-right: 1px solid #222; }
    QListWidget#NavList { border: none; background-color: transparent; outline: none; }

    /* Scrollbars */
    QScrollBar:vertical {
        border: none;
        background: #111;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #333;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        border: none;
        background: none;
    }
    QListWidget#NavList::item {
        padding: 16px 16px;
        border-radius: 8px;
        margin: 4px 8px;
        color: #888;
        font-weight: 500;
    }
    QListWidget#NavList::item:selected {
        background-color: #1A1A1A;
        color: #FFFFFF;
        border: 1px solid #333;
    }
    QListWidget#NavList::item:hover:!selected {
        background-color: #161616;
        color: #BBB;
    }

    /* Cards */
    QFrame.Card {
        background-color: #141414;
        border-radius: 12px;
        border: 1px solid #252525;
    }
    QFrame.Card:hover {
        border: 1px solid #353535;
    }

    /* Buttons */
    QPushButton {
        padding: 10px 18px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 13px;
        border: 1px solid transparent;
    }
    QPushButton#PrimaryAction {
        background-color: #2D63ED;
        color: white;
    }
    QPushButton#PrimaryAction:hover {
        background-color: #3D73FD;
    }
    QPushButton#StopAction {
        background-color: #E03131;
        color: white;
    }
    QPushButton#StopAction:hover {
        background-color: #F04141;
    }
    QPushButton#SecondaryAction {
        background-color: #222;
        color: #EEE;
        border: 1px solid #333;
    }
    QPushButton#SecondaryAction:hover {
        background-color: #2A2A2A;
    }

    /* Inputs */
    QLineEdit, QSpinBox, QComboBox, QTextEdit {
        background-color: #111;
        color: #EEE;
        border: 1px solid #222;
        padding: 10px;
        border-radius: 8px;
        selection-background-color: #2D63ED;
    }
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {
        border: 1px solid #444;
        background-color: #141414;
    }

    /* Tables */
    QTableWidget {
        background-color: transparent;
        border: none;
        color: #DDD;
        gridline-color: #222;
        outline: none;
    }
    QHeaderView::section {
        background-color: #161616;
        color: #999;
        padding: 12px;
        border: none;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
    }
    QTableWidget::item { padding: 12px; }

    /* Tabs */
    QTabWidget::pane { border: 1px solid #222; background: #141414; border-radius: 8px; top: -1px; }
    QTabBar::tab {
        background: transparent;
        color: #777;
        padding: 12px 24px;
        font-weight: 600;
        border-bottom: 2px solid transparent;
    }
    QTabBar::tab:selected {
        color: #2D63ED;
        border-bottom: 2px solid #2D63ED;
    }
    QTabBar::tab:hover:!selected { color: #BBB; }

    /* Progress Bar */
    QProgressBar {
        height: 8px;
        border-radius: 4px;
        background-color: #1A1A1A;
        text-align: center;
        border: none;
    }
    QProgressBar::chunk {
        background-color: #2D63ED;
        border-radius: 4px;
    }
"""

# Setup Logging for UI
class UsageChart(QWidget):
    def __init__(self):
        super().__init__()
        self.data = []  # List of {"day": str, "sent": int, "received": int}
        self.setMinimumHeight(220)

    def setData(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        padding_x = 50
        padding_y = 40

        chart_width = width - 2 * padding_x
        chart_height = height - 2 * padding_y

        max_val = max((d['sent'] + d['received']) for d in self.data) if self.data else 1
        if max_val == 0: max_val = 1

        num_days = len(self.data)
        bar_width = (chart_width / num_days) * 0.5 if num_days > 0 else 0
        spacing = (chart_width / num_days) * 0.5 if num_days > 0 else 0

        # Draw Grid Lines
        painter.setPen(QPen(QColor("#222"), 1))
        for i in range(5):
            y_line = height - padding_y - (i * chart_height / 4)
            painter.drawLine(padding_x, int(y_line), width - padding_x, int(y_line))

        # Draw bars
        for i, day in enumerate(self.data):
            total = day['sent'] + day['received']
            h = (total / max_val) * chart_height

            x = padding_x + i * (bar_width + spacing) + spacing / 2
            y = height - padding_y - h

            # Received bar (bottom)
            h_rec = (day['received'] / max_val) * chart_height
            painter.setBrush(QBrush(QColor("#2D63ED")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), int(height - padding_y - h_rec), int(bar_width), int(h_rec), 4, 4)

            # Sent bar (top)
            if day['sent'] > 0:
                h_sent = (day['sent'] / max_val) * chart_height
                painter.setBrush(QBrush(QColor("#00BFA5")))
                painter.drawRoundedRect(int(x), int(height - padding_y - h_rec - h_sent), int(bar_width), int(h_sent), 4, 4)

            # Label
            painter.setPen(QColor("#666"))
            painter.setFont(QFont("Inter", 8, QFont.Weight.Medium))
            label = day['day'][-5:] # MM-DD
            painter.drawText(int(x), height - padding_y + 20, int(bar_width), 20, Qt.AlignmentFlag.AlignCenter, label)

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

class ScriptIdItem(QWidget):
    deleted = pyqtSignal(object)

    def __init__(self, script_id="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.edit = QLineEdit(script_id)
        self.edit.setPlaceholderText("Enter Apps Script ID")
        layout.addWidget(self.edit)

        self.del_btn = QPushButton()
        self.del_btn.setIcon(qta.icon("fa5s.trash-alt", color="#e74c3c"))
        self.del_btn.setFixedSize(40, 40)
        self.del_btn.setObjectName("SecondaryAction")
        self.del_btn.clicked.connect(lambda: self.deleted.emit(self))
        layout.addWidget(self.del_btn)

class ScriptIdList(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(10)

        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(8)
        self.items_layout.addStretch()

        self.main_layout.addWidget(self.items_container)

        self.add_btn = QPushButton("Add Script ID")
        self.add_btn.setIcon(qta.icon("fa5s.plus", color="white"))
        self.add_btn.setObjectName("SecondaryAction")
        self.add_btn.clicked.connect(lambda: self.add_item())
        self.main_layout.addWidget(self.add_btn)

        self.items = []

    def add_item(self, script_id=""):
        item = ScriptIdItem(script_id)
        item.deleted.connect(self.remove_item)
        # Insert before the stretch
        self.items_layout.insertWidget(len(self.items), item)
        self.items.append(item)
        return item

    def remove_item(self, item):
        if len(self.items) <= 1 and not item.edit.text():
            # Don't remove the last empty one, just clear it
            return

        self.items.remove(item)
        item.deleteLater()
        if not self.items:
            self.add_item()

    def set_ids(self, ids):
        # Clear existing
        for item in self.items:
            item.deleteLater()
        self.items = []

        if not ids:
            self.add_item()
        else:
            if isinstance(ids, str):
                ids = [ids]
            for sid in ids:
                self.add_item(sid)

    def get_ids(self):
        return [item.edit.text().strip() for item in self.items if item.edit.text().strip()]

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
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 32, 0, 16)
        sidebar_layout.setSpacing(8)

        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(24, 0, 24, 24)

        logo_icon = QLabel()
        logo_icon.setPixmap(qta.icon("fa5s.shield-alt", color="#2D63ED").pixmap(28, 28))
        logo_layout.addWidget(logo_icon)

        logo_label = QLabel("MasterRelay")
        logo_label.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        logo_label.setStyleSheet("color: white; letter-spacing: -0.5px;")
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
        ]

        for text, icon in items:
            item = QListWidgetItem(qta.icon(icon, color="#888"), text)
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
        self.content_stack.setStyleSheet("background-color: #0A0A0A; color: #e0e0e0;")

        self.dashboard_page = self._create_dashboard_page()
        self.monitoring_page = self._create_monitoring_page()
        self.routing_page = self._create_routing_page()
        self.settings_page = self._create_settings_page()
        self.logs_page = self._create_logs_page()
        self.scanner_page = self._create_scanner_page()

        self.content_stack.addWidget(self.dashboard_page)
        self.content_stack.addWidget(self.monitoring_page)
        self.content_stack.addWidget(self.routing_page)
        self.content_stack.addWidget(self.settings_page)
        self.content_stack.addWidget(self.logs_page)
        self.content_stack.addWidget(self.scanner_page)

        main_layout.addWidget(self.content_stack)

    def _create_dashboard_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(32)

        header_layout = QHBoxLayout()
        header = QLabel("Dashboard")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFF; letter-spacing: -1px;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        self.toggle_btn = QPushButton("Start Proxy")
        self.toggle_btn.setObjectName("PrimaryAction")
        self.toggle_btn.setMinimumWidth(160)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle_proxy)
        header_layout.addWidget(self.toggle_btn)
        layout.addLayout(header_layout)

        # Status and Health Section
        cards_row = QHBoxLayout()
        cards_row.setSpacing(24)

        # Status Card
        self.status_card = QFrame()
        self.status_card.setProperty("class", "Card")
        status_layout = QVBoxLayout(self.status_card)
        status_layout.setContentsMargins(24, 24, 24, 24)

        status_header = QHBoxLayout()
        self.status_icon = QLabel()
        self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#444").pixmap(14, 14))
        status_header.addWidget(self.status_icon)

        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #999; letter-spacing: 1px;")
        status_header.addWidget(self.status_label)
        status_header.addStretch()
        status_layout.addLayout(status_header)

        self.status_detail = QLabel("Ready to secure your connection")
        self.status_detail.setFont(QFont("Inter", 16, QFont.Weight.Medium))
        self.status_detail.setStyleSheet("color: #EEE; margin-top: 8px;")
        status_layout.addWidget(self.status_detail)

        cards_row.addWidget(self.status_card, 2)

        # Relay Health Card
        self.health_card = QFrame()
        self.health_card.setProperty("class", "Card")
        health_layout = QVBoxLayout(self.health_card)
        health_layout.setContentsMargins(24, 24, 24, 24)

        health_title = QLabel("RELAY HEALTH")
        health_title.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        health_title.setStyleSheet("color: #999; letter-spacing: 1px;")
        health_layout.addWidget(health_title)

        self.health_list = QLabel("No active scripts")
        self.health_list.setStyleSheet("color: #BBB; font-size: 13px; margin-top: 8px;")
        self.health_list.setWordWrap(True)
        health_layout.addWidget(self.health_list)
        health_layout.addStretch()
        cards_row.addWidget(self.health_card, 1)

        layout.addLayout(cards_row)

        # Stats Area
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(24)

        def create_stat_box(title, value, icon, color):
            box = QFrame()
            box.setProperty("class", "Card")
            blayout = QVBoxLayout(box)
            blayout.setContentsMargins(24, 24, 24, 24)

            top_box = QHBoxLayout()
            tlabel = QLabel(title.upper())
            tlabel.setStyleSheet("color: #999; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
            top_box.addWidget(tlabel)
            top_box.addStretch()
            ilabel = QLabel()
            ilabel.setPixmap(qta.icon(icon, color=color).pixmap(20, 20))
            top_box.addWidget(ilabel)
            blayout.addLayout(top_box)

            vlabel = QLabel(value)
            vlabel.setFont(QFont("Inter", 24, QFont.Weight.Bold))
            vlabel.setStyleSheet("color: #FFF; margin-top: 4px;")
            blayout.addWidget(vlabel)
            return box, vlabel

        self.stat_box_1, self.val_requests = create_stat_box("Requests", "0", "fa5s.exchange-alt", "#2D63ED")
        self.stat_box_2, self.val_data = create_stat_box("Bandwidth", "0 MB", "fa5s.database", "#00BFA5")
        self.stat_box_3, self.val_latency = create_stat_box("Latency", "0 ms", "fa5s.bolt", "#FFD600")

        stats_layout.addWidget(self.stat_box_1)
        stats_layout.addWidget(self.stat_box_2)
        stats_layout.addWidget(self.stat_box_3)
        layout.addLayout(stats_layout)

        # Quota Card
        quota_card = QFrame()
        quota_card.setProperty("class", "Card")
        quota_layout = QVBoxLayout(quota_card)
        quota_layout.setContentsMargins(24, 24, 24, 24)

        quota_header = QHBoxLayout()
        quota_title = QLabel("DAILY USAGE QUOTA")
        quota_title.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        quota_title.setStyleSheet("color: #999; letter-spacing: 1px;")
        quota_header.addWidget(quota_title)
        quota_header.addStretch()

        script_ids = self.config.get("script_ids") or self.config.get("script_id")
        num_scripts = len(script_ids) if isinstance(script_ids, list) else (1 if script_ids else 0)
        initial_limit = 20000 * num_scripts if num_scripts > 0 else 20000

        self.quota_label = QLabel(f"0 / {initial_limit}")
        self.quota_label.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self.quota_label.setStyleSheet("color: #EEE;")
        quota_header.addWidget(self.quota_label)
        quota_layout.addLayout(quota_header)

        self.quota_progress = QProgressBar()
        self.quota_progress.setMaximum(initial_limit)
        self.quota_progress.setValue(0)
        self.quota_progress.setTextVisible(False)
        quota_layout.addWidget(self.quota_progress)

        self.quota_hint = QLabel("Resets daily at 10:30 AM")
        self.quota_hint.setStyleSheet("color: #555; font-size: 12px; margin-top: 4px;")
        quota_layout.addWidget(self.quota_hint)

        layout.addWidget(quota_card)

        layout.addStretch()
        return page

    def _create_routing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()
        header = QLabel("Routing Rules")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFF; letter-spacing: -1px;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        btn_quick = QPushButton("Quick Add")
        btn_quick.setIcon(qta.icon("fa5s.bolt", color="white"))
        btn_quick.setObjectName("SecondaryAction")
        btn_quick.clicked.connect(self._quick_add_rule)
        header_layout.addWidget(btn_quick)

        btn_add = QPushButton("Add Group")
        btn_add.setIcon(qta.icon("fa5s.plus", color="white"))
        btn_add.setObjectName("PrimaryAction")
        btn_add.clicked.connect(self._add_routing_ruleset)
        header_layout.addWidget(btn_add)
        layout.addLayout(header_layout)

        desc = QLabel("Define how domains, IPs, or CIDR ranges should be routed. Exact domains match their subdomains.")
        desc.setStyleSheet("color: #777; font-size: 14px;")
        layout.addWidget(desc)

        self.routing_table = QTableWidget(0, 5)
        self.routing_table.setHorizontalHeaderLabels(["ON", "RULE / GROUP NAME", "MODE", "RULES", "ACTIONS"])
        self.routing_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.routing_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.routing_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.routing_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.routing_table.verticalHeader().setDefaultSectionSize(50)
        layout.addWidget(self.routing_table)

        self._refresh_routing_table()
        return page

    def _refresh_routing_table(self):
        groups = self.config.get("rule_groups") or self.config.get("bypass_groups") or []
        self.routing_table.setRowCount(len(groups))

        for i, group in enumerate(groups):
            # Enabled Checkbox
            check_widget = QWidget()
            check_layout = QHBoxLayout(check_widget)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb = QCheckBox()
            cb.setChecked(group.get("enabled", True))
            cb.stateChanged.connect(lambda state, idx=i: self._toggle_group_enabled(idx, state))
            check_layout.addWidget(cb)
            self.routing_table.setCellWidget(i, 0, check_widget)

            # Name
            self.routing_table.setItem(i, 1, QTableWidgetItem(group.get("name", "Unnamed")))

            # Mode
            mode = group.get("mode", "direct").upper()
            mode_item = QTableWidgetItem(mode)
            if mode == "RELAY": mode_item.setForeground(QColor("#3498db"))
            elif mode == "DIRECT": mode_item.setForeground(QColor("#2ecc71"))
            elif mode == "BLOCK": mode_item.setForeground(QColor("#e74c3c"))
            self.routing_table.setItem(i, 2, mode_item)

            # Rules Summary
            rules = group.get("rules", [])
            url = group.get("update_url", "")
            if url:
                summary = f"Subscription: {url[:30]}..."
            else:
                summary = f"{len(rules)} items: {', '.join(rules[:3])}"
                if len(rules) > 3: summary += "..."

            self.routing_table.setItem(i, 3, QTableWidgetItem(summary))

            # Actions
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(8)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_edit = QPushButton()
            btn_edit.setIcon(qta.icon("fa5s.edit", color="white"))
            btn_edit.setToolTip("Edit Rule")
            btn_edit.setFixedSize(34, 34)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setObjectName("SecondaryAction")
            btn_edit.clicked.connect(lambda checked, idx=i: self._edit_routing_ruleset(idx))
            action_layout.addWidget(btn_edit)

            if url:
                btn_update = QPushButton()
                btn_update.setIcon(qta.icon("fa5s.sync-alt", color="white"))
                btn_update.setToolTip("Update Now")
                btn_update.setFixedSize(34, 34)
                btn_update.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_update.setObjectName("SecondaryAction")
                btn_update.clicked.connect(lambda checked, idx=i: self._update_group_rules(idx))
                action_layout.addWidget(btn_update)

            btn_del = QPushButton()
            btn_del.setIcon(qta.icon("fa5s.trash-alt", color="#E03131"))
            btn_del.setToolTip("Delete Rule")
            btn_del.setFixedSize(34, 34)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setObjectName("SecondaryAction")
            btn_del.clicked.connect(lambda checked, idx=i: self._delete_routing_ruleset(idx))
            action_layout.addWidget(btn_del)

            self.routing_table.setCellWidget(i, 4, action_widget)

    def _quick_add_rule(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Quick Add Routing Rule")
        dialog.setMinimumWidth(400)
        d_layout = QVBoxLayout(dialog)

        form = QFormLayout()
        edit_host = QLineEdit()
        edit_host.setPlaceholderText("e.g., example.com or 1.1.1.1")
        form.addRow("Domain/IP:", edit_host)

        edit_mode = QComboBox()
        edit_mode.addItems(["Relay", "Direct", "Block"])
        form.addRow("Mode:", edit_mode)
        d_layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        d_layout.addWidget(buttons)

        if dialog.exec():
            host = edit_host.text().strip()
            if not host: return
            mode = edit_mode.currentText().lower()

            if "rule_groups" not in self.config:
                self.config["rule_groups"] = self.config.get("bypass_groups", [])
                if "bypass_groups" in self.config: del self.config["bypass_groups"]

            # Find or create "General Rules" group for this mode
            group_name = f"General {mode.capitalize()} Rules"
            target_group = None
            for g in self.config.get("rule_groups", []):
                if g["name"] == group_name and g["mode"] == mode and not g.get("update_url"):
                    target_group = g
                    break

            if not target_group:
                target_group = {
                    "name": group_name,
                    "enabled": True,
                    "mode": mode,
                    "rules": [],
                    "update_url": ""
                }
                if "rule_groups" not in self.config: self.config["rule_groups"] = []
                self.config["rule_groups"].append(target_group)

            if host not in target_group["rules"]:
                target_group["rules"].append(host)
                self._save_config()
                self._refresh_routing_table()
                logging.info(f"Added {host} to {group_name}")

    def _add_routing_ruleset(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Routing Rule")
        dialog.setMinimumWidth(400)
        d_layout = QVBoxLayout(dialog)

        form = QFormLayout()
        edit_name = QLineEdit()
        edit_name.setPlaceholderText("e.g., My Direct Sites")
        form.addRow("Group Name:", edit_name)

        edit_mode = QComboBox()
        edit_mode.addItems(["Relay", "Direct", "Block"])
        form.addRow("Mode:", edit_mode)
        d_layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        d_layout.addWidget(buttons)

        if dialog.exec():
            name = edit_name.text() or "New Rule Group"
            if "rule_groups" not in self.config:
                self.config["rule_groups"] = self.config.get("bypass_groups", [])
                if "bypass_groups" in self.config: del self.config["bypass_groups"]

            self.config["rule_groups"].append({
                "name": name,
                "enabled": True,
                "mode": edit_mode.currentText().lower(),
                "rules": [],
                "update_url": ""
            })
            self._save_config()
            self._refresh_routing_table()

    def _toggle_group_enabled(self, index, state):
        groups = self.config.get("rule_groups") or self.config.get("bypass_groups") or []
        if 0 <= index < len(groups):
            groups[index]["enabled"] = (state == Qt.CheckState.Checked.value)
            self._save_config()

    def _edit_routing_ruleset(self, index):
        groups = self.config.get("rule_groups") or self.config.get("bypass_groups") or []
        if 0 <= index < len(groups):
            group = groups[index]

            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit Group: {group['name']}")
            dialog.setMinimumSize(500, 450)
            d_layout = QVBoxLayout(dialog)

            form = QFormLayout()
            edit_name = QLineEdit(group['name'])
            form.addRow("Name:", edit_name)

            edit_mode = QComboBox()
            edit_mode.addItems(["Direct", "Block", "Relay"])
            edit_mode.setCurrentText(group.get("mode", "direct").capitalize())
            form.addRow("Mode:", edit_mode)

            edit_url = QLineEdit(group.get('update_url', ''))
            form.addRow("Update URL:", edit_url)
            d_layout.addLayout(form)

            d_layout.addWidget(QLabel("Rules (one per line, supports domains, .suffixes, and IPs/CIDR):"))
            edit_rules = QTextEdit()
            edit_rules.setPlainText("\n".join(group.get('rules', [])))
            d_layout.addWidget(edit_rules)

            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            d_layout.addWidget(buttons)

            if dialog.exec():
                group['name'] = edit_name.text()
                group['mode'] = edit_mode.currentText().lower()
                group['update_url'] = edit_url.text()
                group['rules'] = [r.strip() for r in edit_rules.toPlainText().split("\n") if r.strip()]
                # Migrate to rule_groups if not already
                if "bypass_groups" in self.config:
                    self.config["rule_groups"] = groups
                    del self.config["bypass_groups"]
                self._save_config()
                self._refresh_routing_table()

    def _delete_routing_ruleset(self, index):
        ret = QMessageBox.question(self, "Delete Group", "Are you sure you want to delete this group?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            groups = self.config.get("rule_groups") or self.config.get("bypass_groups") or []
            if 0 <= index < len(groups):
                groups.pop(index)
                if "bypass_groups" in self.config:
                    self.config["rule_groups"] = groups
                    del self.config["bypass_groups"]
                self._save_config()
                self._refresh_routing_table()

    def _update_group_rules(self, index):
        if not self.proxy_service.is_running:
            logging.warning("Start the proxy first to enable background updates.")
            return

        # We need to run the async update_bypass_group in the service
        async def do_update():
            success = await self.proxy_service.update_bypass_group(index)
            if success:
                self._save_config()
                # Refresh UI safely from the main thread
                QTimer.singleShot(0, self._refresh_routing_table)
                logging.info(f"Group {index} updated successfully.")
            else:
                logging.error(f"Failed to update group {index}.")

        asyncio.run_coroutine_threadsafe(do_update(), self.proxy_service.loop)

    def _create_monitoring_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()
        header = QLabel("Monitoring")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setStyleSheet("color: white; letter-spacing: -1px;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        range_label = QLabel("TIME RANGE")
        range_label.setStyleSheet("color: #999; font-weight: 700; font-size: 11px; letter-spacing: 1px;")
        header_layout.addWidget(range_label)
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["Last 24 Hours", "Last 7 Days", "Last 30 Days"])
        self.time_range_combo.setMinimumWidth(150)
        header_layout.addWidget(self.time_range_combo)
        layout.addLayout(header_layout)

        # Top 10 Table
        table_container = QFrame()
        table_container.setProperty("class", "Card")
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(24, 24, 24, 24)

        table_header = QLabel("TOP 10 ACTIVE HOSTS")
        table_header.setStyleSheet("color: #999; font-weight: 700; font-size: 11px; letter-spacing: 1px;")
        table_layout.addWidget(table_header)

        self.usage_table = QTableWidget(0, 5)
        self.usage_table.setHorizontalHeaderLabels(["HOST", "REQUESTS", "UPLOAD", "DOWNLOAD", "TOTAL"])
        self.usage_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.usage_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table_layout.addWidget(self.usage_table)
        layout.addWidget(table_container)

        # History Chart Placeholder
        chart_container = QFrame()
        chart_container.setProperty("class", "Card")
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(24, 24, 24, 24)

        chart_title = QLabel("TRAFFIC HISTORY")
        chart_title.setStyleSheet("color: #999; font-weight: 700; font-size: 11px; letter-spacing: 1px;")
        chart_layout.addWidget(chart_title)

        self.usage_chart = UsageChart()
        chart_layout.addWidget(self.usage_chart)

        self.history_summary = QLabel()
        self.history_summary.setStyleSheet("color: #555; font-family: 'Inter'; font-size: 12px; margin-top: 12px;")
        chart_layout.addWidget(self.history_summary)

        layout.addWidget(chart_container)

        return page

    def _create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header = QHBoxLayout()
        header_text = QLabel("Settings")
        header_text.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header_text.setStyleSheet("color: #FFF; letter-spacing: -1px;")
        header.addWidget(header_text)
        header.addStretch()

        btn_import = QPushButton("Import")
        btn_import.setIcon(qta.icon("fa5s.file-import", color="white"))
        btn_import.setObjectName("SecondaryAction")
        btn_import.clicked.connect(self._import_config)
        header.addWidget(btn_import)

        btn_export = QPushButton("Export")
        btn_export.setIcon(qta.icon("fa5s.file-export", color="white"))
        btn_export.setObjectName("SecondaryAction")
        btn_export.clicked.connect(self._export_config)
        header.addWidget(btn_export)

        btn_reformat = QPushButton("Reformat Config")
        btn_reformat.setIcon(qta.icon("fa5s.magic", color="white"))
        btn_reformat.setObjectName("SecondaryAction")
        btn_reformat.clicked.connect(self._reformat_config)
        header.addWidget(btn_reformat)

        layout.addLayout(header)

        tabs = QTabWidget()

        # Styles for Inputs
        label_style = "color: #999; font-weight: 600; font-size: 13px;"

        def create_form_tab():
            w = QWidget()
            f = QFormLayout(w)
            f.setSpacing(15)
            f.setContentsMargins(20, 20, 20, 20)
            return w, f

        def add_row(form, label, widget):
            lbl = QLabel(label)
            lbl.setStyleSheet(label_style)
            form.addRow(lbl, widget)

        # Tab 1: General
        general_w, general_f = create_form_tab()

        script_ids = self.config.get("script_ids") or self.config.get("script_id", "")

        self.script_id_list = ScriptIdList()
        self.script_id_list.set_ids(script_ids)

        # Wrap in scroll area if it gets long
        script_scroll = QScrollArea()
        script_scroll.setWidgetResizable(True)
        script_scroll.setWidget(self.script_id_list)
        script_scroll.setMinimumHeight(150)
        script_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        add_row(general_f, "Apps Script IDs:", script_scroll)

        self.edit_auth_key = QLineEdit(self.config.get("auth_key", ""))
        self.edit_auth_key.setEchoMode(QLineEdit.EchoMode.Password)
        add_row(general_f, "Auth Key:", self.edit_auth_key)

        self.edit_google_ip = QLineEdit(self.config.get("google_ip", "216.239.38.120"))
        add_row(general_f, "Google Frontend IP:", self.edit_google_ip)

        self.edit_default_mode = QComboBox()
        self.edit_default_mode.addItems(["Relay", "Direct", "Block"])
        self.edit_default_mode.setCurrentText(self.config.get("default_connection_mode", "relay").capitalize())
        add_row(general_f, "Default Connection Mode:", self.edit_default_mode)

        tabs.addTab(general_w, "General")

        # Tab 2: Network
        network_w, network_f = create_form_tab()
        self.edit_listen_port = QLineEdit(str(self.config.get("listen_port", 8085)))
        add_row(network_f, "HTTP Proxy Port:", self.edit_listen_port)

        self.edit_socks_port = QLineEdit(str(self.config.get("socks5_port", 1080)))
        add_row(network_f, "SOCKS5 Port:", self.edit_socks_port)

        self.check_lan = QCheckBox("Allow LAN connections")
        self.check_lan.setChecked(self.config.get("lan_sharing", False))
        add_row(network_f, "", self.check_lan)

        tabs.addTab(network_w, "Network")

        # Tab 3: Relay Settings
        relay_w, relay_f = create_form_tab()
        self.spin_parallel = QSpinBox()
        self.spin_parallel.setRange(1, 10)
        self.spin_parallel.setValue(self.config.get("parallel_relay", 1))
        add_row(relay_f, "Parallel Relay Count:", self.spin_parallel)

        self.check_youtube_relay = QCheckBox("Route YouTube through Relay")
        self.check_youtube_relay.setChecked(self.config.get("youtube_via_relay", False))
        add_row(relay_f, "YouTube Relay:", self.check_youtube_relay)

        self.edit_bypass_hosts = QTextEdit()
        self.edit_bypass_hosts.setPlainText("\n".join(self.config.get("bypass_hosts", [])))
        add_row(relay_f, "Bypass Hosts:", self.edit_bypass_hosts)

        tabs.addTab(relay_w, "Relay")

        # Tab 4: Exit Node
        exit_node_w, exit_node_f = create_form_tab()
        exit_cfg = self.config.get("exit_node", {})

        self.check_exit_enabled = QCheckBox("Enable Exit Node (Chain Relay)")
        self.check_exit_enabled.setChecked(exit_cfg.get("enabled", False))
        add_row(exit_node_f, "Status:", self.check_exit_enabled)

        self.combo_exit_provider = QComboBox()
        provider_map = {"custom": "Custom", "valtown": "ValTown", "cloudflare": "Cloudflare", "deno": "Deno", "vps": "VPS"}
        self.combo_exit_provider.addItems(list(provider_map.values()))
        provider_key = exit_cfg.get("provider", "custom").lower()
        self.combo_exit_provider.setCurrentText(provider_map.get(provider_key, "Custom"))
        add_row(exit_node_f, "Provider:", self.combo_exit_provider)

        self.edit_exit_url = QLineEdit(exit_cfg.get("url", ""))
        self.edit_exit_url.setPlaceholderText("https://your-exit-node-url.com")
        add_row(exit_node_f, "Exit Node URL:", self.edit_exit_url)

        self.edit_exit_psk = QLineEdit(exit_cfg.get("psk", ""))
        self.edit_exit_psk.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_exit_psk.setPlaceholderText("Pre-Shared Key (Optional)")
        add_row(exit_node_f, "Auth PSK:", self.edit_exit_psk)

        self.combo_exit_mode = QComboBox()
        self.combo_exit_mode.addItems(["Selective", "Full"])
        self.combo_exit_mode.setCurrentText(exit_cfg.get("mode", "selective").capitalize())
        add_row(exit_node_f, "Routing Mode:", self.combo_exit_mode)

        self.edit_exit_hosts = QTextEdit()
        self.edit_exit_hosts.setPlainText("\n".join(exit_cfg.get("hosts", [])))
        self.edit_exit_hosts.setPlaceholderText("Domains to route via exit node (one per line)")
        add_row(exit_node_f, "Selective Hosts:", self.edit_exit_hosts)

        tabs.addTab(exit_node_w, "Exit Node")

        layout.addWidget(tabs)

        self.restart_hint = QLabel("Note: Changes to ports or LAN sharing require a proxy restart.")
        self.restart_hint.setStyleSheet("color: #e67e22; font-size: 11px; margin-top: 5px;")
        self.restart_hint.setVisible(False)
        layout.addWidget(self.restart_hint)

        btn_save = QPushButton("Save Settings")
        btn_save.setMinimumWidth(160)
        btn_save.setObjectName("PrimaryAction")
        btn_save.clicked.connect(self._save_settings_from_ui)
        layout.addWidget(btn_save, alignment=Qt.AlignmentFlag.AlignRight)

        return page

    def _create_logs_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header = QHBoxLayout()
        header_text = QLabel("System Logs")
        header_text.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header_text.setStyleSheet("color: #FFF; letter-spacing: -1px;")
        header.addWidget(header_text)
        header.addStretch()

        btn_clear = QPushButton("Clear Logs")
        btn_clear.setObjectName("SecondaryAction")
        btn_clear.clicked.connect(lambda: self.log_view.clear())
        header.addWidget(btn_clear)
        layout.addLayout(header)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            QTextEdit { background-color: #050505; color: #BBB; font-family: 'Consolas', monospace; font-size: 12px; border: 1px solid #222; }
        """)
        layout.addWidget(self.log_view)

        return page

    def _create_scanner_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()
        header = QLabel("IP Scanner")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setStyleSheet("color: #FFF; letter-spacing: -1px;")
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
        self.scanner_results.setStyleSheet("""
            QTextEdit { background-color: #050505; color: #BBB; font-family: 'Consolas', monospace; border: 1px solid #222; }
        """)
        layout.addWidget(self.scanner_results)

        return page

    # Handlers
    def _on_nav_changed(self, index):
        # Fade effect
        eff = QGraphicsOpacityEffect(self.content_stack)
        self.content_stack.setGraphicsEffect(eff)

        # Store animation as class attribute to prevent garbage collection
        self._nav_anim = QPropertyAnimation(eff, b"opacity")
        self._nav_anim.setDuration(250)
        self._nav_anim.setStartValue(0.2)
        self._nav_anim.setEndValue(1.0)
        self._nav_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self.content_stack.setCurrentIndex(index)
        self._nav_anim.start()

    def _toggle_proxy(self):
        if self.proxy_service.is_running:
            self.proxy_service.stop()
        else:
            self._save_settings_from_ui()
            self.proxy_service.config = self.config
            self.proxy_service.start()

    def _on_proxy_status_change(self, status):
        if status == "starting":
            self.status_label.setText("STARTING...")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#f1c40f").pixmap(14, 14))
            self.toggle_btn.setEnabled(False)
        elif status == "stopped":
            self.status_label.setText("DISCONNECTED")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#444").pixmap(14, 14))
            self.toggle_btn.setText("Start Proxy")
            self.toggle_btn.setObjectName("PrimaryAction")
            self.toggle_btn.setStyle(self.toggle_btn.style()) # Refresh style
            self.toggle_btn.setEnabled(True)
            self.status_detail.setText("Ready to secure your connection")
        elif "error" in status:
            self.status_label.setText("ERROR")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#e74c3c").pixmap(14, 14))
            self.status_detail.setText(status)
            self.toggle_btn.setText("Start Proxy")
            self.toggle_btn.setEnabled(True)
        else:
            # Running
            self.status_label.setText("CONNECTED")
            self.status_label.setStyleSheet("color: #00BFA5; letter-spacing: 1px;")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#00BFA5").pixmap(14, 14))
            self.toggle_btn.setText("Stop Proxy")
            self.toggle_btn.setObjectName("StopAction")
            self.toggle_btn.setStyle(self.toggle_btn.style()) # Refresh style
            self.toggle_btn.setEnabled(True)
            self.status_detail.setText(f"Listening on port {self.config.get('listen_port')}")

    def _update_stats(self):
        try:
            self._update_stats_impl()
        except Exception as e:
            logging.debug(f"Stats update error: {e}")

    def _update_stats_impl(self):
        # Update Quota Hint with next reset time
        now = datetime.now()
        reset_today = now.replace(hour=10, minute=30, second=0, microsecond=0)
        if now >= reset_today:
            next_reset = reset_today + timedelta(days=1)
        else:
            next_reset = reset_today

        diff = next_reset - now
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        self.quota_hint.setText(f"Next reset in {hours}h {minutes}m (at 10:30 AM)")

        days_map = {"Last 24 Hours": 1, "Last 7 Days": 7, "Last 30 Days": 30}
        selected_range = self.time_range_combo.currentText()
        days = days_map.get(selected_range, 1)

        usage = self.proxy_service.get_usage(days=days)
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

            # Update Relay Health
            stats = self.proxy_service.get_stats()
            if stats:
                blacklisted = stats.get("blacklisted_scripts", [])
                script_ids = self.config.get("script_ids") or self.config.get("script_id")
                if not isinstance(script_ids, list): script_ids = [script_ids] if script_ids else []

                health_text = []
                for sid in script_ids:
                    short_id = sid[-8:] if len(sid) > 8 else sid
                    is_blacklisted = any(b['sid'] == sid[-12:] or b['sid'] == sid for b in blacklisted)
                    if is_blacklisted:
                        health_text.append(f"<span style='color: #e74c3c;'>✖ {short_id} (Failing)</span>")
                    else:
                        health_text.append(f"<span style='color: #2ecc71;'>✔ {short_id} (Healthy)</span>")

                if health_text:
                    self.health_list.setText("<br>".join(health_text))
                else:
                    self.health_list.setText("No scripts configured")

            # Update Monitoring Table
            top_hosts = usage.get("top_hosts", [])
            self.usage_table.setRowCount(len(top_hosts))
            for i, h in enumerate(top_hosts):
                self.usage_table.setItem(i, 0, QTableWidgetItem(h['host']))
                self.usage_table.setItem(i, 1, QTableWidgetItem(str(h.get('requests', 0))))
                self.usage_table.setItem(i, 2, QTableWidgetItem(f"{h['sent']/1024/1024:.2f} MB"))
                self.usage_table.setItem(i, 3, QTableWidgetItem(f"{h['received']/1024/1024:.2f} MB"))
                self.usage_table.setItem(i, 4, QTableWidgetItem(f"{h['total']/1024/1024:.2f} MB"))

            # Update History Chart
            history = usage.get("history", [])
            self.usage_chart.setData(history)

            history_text = "Recent History:\n"
            for day in history[-3:]:
                history_text += f"{day['day']}: Up: {day['sent']/1024/1024:.1f}MB, Down: {day['received']/1024/1024:.1f}MB\n"
            self.history_summary.setText(history_text)

        # Total Stats from DB (Persistent)
        total_usage = self.proxy_service.get_total_usage()
        if total_usage:
            self.val_requests.setText(str(total_usage['total_requests']))
            self.val_data.setText(f"{total_usage['total_bytes'] / (1024*1024):.1f} MB")

        # Current Session Latency
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

    def _save_settings_from_ui(self):
        self.restart_hint.setVisible(True)

        script_ids = self.script_id_list.get_ids()
        if len(script_ids) == 1:
            self.config["script_id"] = script_ids[0]
            if "script_ids" in self.config: del self.config["script_ids"]
        elif len(script_ids) > 1:
            self.config["script_ids"] = script_ids
            if "script_id" in self.config: del self.config["script_id"]
        else:
            # Fallback if empty
            self.config["script_id"] = ""
            if "script_ids" in self.config: del self.config["script_ids"]

        self.config["auth_key"] = self.edit_auth_key.text()
        self.config["google_ip"] = self.edit_google_ip.text()
        self.config["default_connection_mode"] = self.edit_default_mode.currentText().lower()
        try:
            self.config["listen_port"] = int(self.edit_listen_port.text())
            self.config["socks5_port"] = int(self.edit_socks_port.text())
        except:
            pass
        self.config["lan_sharing"] = self.check_lan.isChecked()
        self.config["parallel_relay"] = self.spin_parallel.value()
        self.config["youtube_via_relay"] = self.check_youtube_relay.isChecked()

        # Exit Node
        if "exit_node" not in self.config:
            self.config["exit_node"] = {}
        self.config["exit_node"]["enabled"] = self.check_exit_enabled.isChecked()
        self.config["exit_node"]["provider"] = self.combo_exit_provider.currentText().lower()
        self.config["exit_node"]["url"] = self.edit_exit_url.text().strip()
        self.config["exit_node"]["psk"] = self.edit_exit_psk.text().strip()
        self.config["exit_node"]["mode"] = self.combo_exit_mode.currentText().lower()
        hosts_text = self.edit_exit_hosts.toPlainText()
        self.config["exit_node"]["hosts"] = [h.strip() for h in hosts_text.split("\n") if h.strip()]

        bypass_text = self.edit_bypass_hosts.toPlainText()
        self.config["bypass_hosts"] = [h.strip() for h in bypass_text.split("\n") if h.strip()]

        self.config["mode"] = "apps_script"
        self._save_config()

        # Update service with new config
        self.proxy_service.update_config(self.config)

    def _import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Config", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "r") as f:
                    new_config = json.load(f)
                    self.config.update(new_config)
                    self._save_config()
                    # Reload UI
                    script_ids = self.config.get("script_ids") or self.config.get("script_id", "")
                    self.script_id_list.set_ids(script_ids)

                    self.edit_auth_key.setText(self.config.get("auth_key", ""))
                    self.edit_google_ip.setText(self.config.get("google_ip", ""))
                    self.edit_listen_port.setText(str(self.config.get("listen_port", 8085)))
                    self.edit_socks_port.setText(str(self.config.get("socks5_port", 1080)))
                    self.check_lan.setChecked(self.config.get("lan_sharing", False))
                    self.spin_parallel.setValue(self.config.get("parallel_relay", 1))
                    self.check_youtube_relay.setChecked(self.config.get("youtube_via_relay", False))

                    exit_cfg = self.config.get("exit_node", {})
                    self.check_exit_enabled.setChecked(exit_cfg.get("enabled", False))
                    provider_map = {"custom": "Custom", "valtown": "ValTown", "cloudflare": "Cloudflare", "deno": "Deno", "vps": "VPS"}
                    provider_key = exit_cfg.get("provider", "custom").lower()
                    self.combo_exit_provider.setCurrentText(provider_map.get(provider_key, "Custom"))
                    self.edit_exit_url.setText(exit_cfg.get("url", ""))
                    self.edit_exit_psk.setText(exit_cfg.get("psk", ""))
                    self.combo_exit_mode.setCurrentText(exit_cfg.get("mode", "selective").capitalize())
                    self.edit_exit_hosts.setPlainText("\n".join(exit_cfg.get("hosts", [])))

                    self.edit_bypass_hosts.setPlainText("\n".join(self.config.get("bypass_hosts", [])))
            except Exception as e:
                logging.error(f"Import failed: {e}")

    def _export_config(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Config", "config_preset.json", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "w") as f:
                    json.dump(self.config, f, indent=2)
            except Exception as e:
                logging.error(f"Export failed: {e}")

    def _reformat_config(self):
        """Prettify and save the current configuration."""
        try:
            self._save_settings_from_ui() # Ensure latest UI changes are captured
            self._save_config() # This already uses indent=2
            logging.info("Configuration reformatted and saved successfully.")
            QMessageBox.information(self, "Success", "Configuration reformatted and saved successfully.")
        except Exception as e:
            logging.error(f"Reformat failed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to reformat config: {e}")

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

    def closeEvent(self, event):
        """Ensure proxy stops when the window is closed."""
        if self.proxy_service.is_running:
            logging.info("Closing window, stopping proxy...")
            self.proxy_service.stop()
        event.accept()

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

    # Try to set application-wide font
    font = QFont("Inter")
    if font.exactMatch():
        app.setFont(font)
    else:
        # Fallback to Segoe UI or Roboto if Inter is missing
        font = QFont("Segoe UI")
        if not font.exactMatch():
            font = QFont("Roboto")
        app.setFont(font)

    window = ModernUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
