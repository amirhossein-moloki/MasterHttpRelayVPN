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
    QInputDialog, QMessageBox, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize, QThread
from PyQt6.QtGui import QFont, QIcon, QColor, QPalette, QTextCursor, QPainter, QPen
import qtawesome as qta

# Ensure src is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from core.proxy_service import ProxyService
from core.constants import __version__
from core.google_ip_scanner import scan_sync

# Setup Logging for UI
class UsageChart(QWidget):
    def __init__(self):
        super().__init__()
        self.data = []  # List of {"day": str, "sent": int, "received": int}
        self.setMinimumHeight(200)

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
        padding = 40

        chart_width = width - 2 * padding
        chart_height = height - 2 * padding

        max_val = max((d['sent'] + d['received']) for d in self.data) if self.data else 1
        if max_val == 0: max_val = 1

        num_days = len(self.data)
        bar_width = (chart_width / num_days) * 0.6 if num_days > 0 else 0
        spacing = (chart_width / num_days) * 0.4 if num_days > 0 else 0

        # Draw axes
        painter.setPen(QPen(QColor("#555"), 2))
        painter.drawLine(padding, height - padding, width - padding, height - padding)
        painter.drawLine(padding, padding, padding, height - padding)

        # Draw bars
        for i, day in enumerate(self.data):
            total = day['sent'] + day['received']
            h = (total / max_val) * chart_height

            x = padding + i * (bar_width + spacing) + spacing / 2
            y = height - padding - h

            # Received bar (bottom)
            h_rec = (day['received'] / max_val) * chart_height
            painter.setBrush(QColor("#3498db"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(int(x), int(height - padding - h_rec), int(bar_width), int(h_rec))

            # Sent bar (top)
            h_sent = (day['sent'] / max_val) * chart_height
            painter.setBrush(QColor("#2ecc71"))
            painter.drawRect(int(x), int(height - padding - h_rec - h_sent), int(bar_width), int(h_sent))

            # Label
            painter.setPen(QColor("#b0b0b0"))
            painter.setFont(QFont("Arial", 8))
            label = day['day'][-5:] # MM-DD
            painter.drawText(int(x), height - padding + 20, label)

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
            ("Routing Rules", "fa5s.route"),
            ("Settings", "fa5s.cog"),
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
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Dashboard")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: white;")
        layout.addWidget(header)

        # Top Section: Status and Relay Health
        top_layout = QHBoxLayout()

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
        top_layout.addWidget(status_card, 2)

        # Relay Health Card
        self.health_card = QFrame()
        self.health_card.setStyleSheet("background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333;")
        health_layout = QVBoxLayout(self.health_card)
        health_title = QLabel("Relay Health")
        health_title.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        health_layout.addWidget(health_title)

        self.health_list = QLabel("No active scripts")
        self.health_list.setStyleSheet("color: #b0b0b0; font-size: 11px;")
        self.health_list.setWordWrap(True)
        health_layout.addWidget(self.health_list)
        health_layout.addStretch()
        top_layout.addWidget(self.health_card, 1)

        layout.addLayout(top_layout)

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
        self.quota_hint.setStyleSheet("color: #7f8c8d; font-size: 11px;")
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

    def _create_routing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        header = QLabel("Routing Rules")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: white;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        btn_quick = QPushButton("Quick Add")
        btn_quick.setIcon(qta.icon("fa5s.bolt", color="white"))
        btn_quick.setStyleSheet("background-color: #f39c12; color: white; padding: 8px 15px; border-radius: 5px; font-weight: bold; margin-right: 10px;")
        btn_quick.clicked.connect(self._quick_add_rule)
        header_layout.addWidget(btn_quick)

        btn_add = QPushButton("Add Group")
        btn_add.setIcon(qta.icon("fa5s.plus", color="white"))
        btn_add.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px 15px; border-radius: 5px; font-weight: bold;")
        btn_add.clicked.connect(self._add_routing_ruleset)
        header_layout.addWidget(btn_add)
        layout.addLayout(header_layout)

        desc = QLabel("Define how domains, IPs, or CIDR ranges should be routed.")
        desc.setStyleSheet("color: #b0b0b0;")
        layout.addWidget(desc)

        self.routing_table = QTableWidget(0, 5)
        self.routing_table.setHorizontalHeaderLabels(["On", "Rule / Group Name", "Mode", "Rules", "Actions"])
        self.routing_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.routing_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.routing_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.routing_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.routing_table.setStyleSheet("""
            QTableWidget { background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333; color: #e0e0e0; gridline-color: #333; }
            QHeaderView::section { background-color: #252525; color: #b0b0b0; padding: 10px; border: 1px solid #333; font-weight: bold; }
        """)
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
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(5)

            btn_edit = QPushButton()
            btn_edit.setIcon(qta.icon("fa5s.edit", color="white"))
            btn_edit.setToolTip("Edit Rule")
            btn_edit.setFixedSize(30, 30)
            btn_edit.setStyleSheet("background-color: #3498db; border-radius: 5px;")
            btn_edit.clicked.connect(lambda checked, idx=i: self._edit_routing_ruleset(idx))
            action_layout.addWidget(btn_edit)

            if url:
                btn_update = QPushButton()
                btn_update.setIcon(qta.icon("fa5s.sync-alt", color="white"))
                btn_update.setToolTip("Update Now")
                btn_update.setFixedSize(30, 30)
                btn_update.setStyleSheet("background-color: #9b59b6; border-radius: 5px;")
                btn_update.clicked.connect(lambda checked, idx=i: self._update_group_rules(idx))
                action_layout.addWidget(btn_update)

            btn_del = QPushButton()
            btn_del.setIcon(qta.icon("fa5s.trash-alt", color="white"))
            btn_del.setToolTip("Delete Rule")
            btn_del.setFixedSize(30, 30)
            btn_del.setStyleSheet("background-color: #e74c3c; border-radius: 5px;")
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
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header_layout = QHBoxLayout()
        header = QLabel("Usage Monitoring")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: white;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        header_layout.addWidget(QLabel("Time Range:"))
        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["Last 24 Hours", "Last 7 Days", "Last 30 Days"])
        self.time_range_combo.setStyleSheet("background-color: #1e1e1e; color: white; padding: 5px; border-radius: 5px;")
        header_layout.addWidget(self.time_range_combo)
        layout.addLayout(header_layout)

        # Top 10 Table
        table_container = QFrame()
        table_container.setStyleSheet("background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333;")
        table_layout = QVBoxLayout(table_container)

        table_header = QLabel("Top 10 Most Active Hosts (Last 24h)")
        table_header.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        table_layout.addWidget(table_header)

        self.usage_table = QTableWidget(0, 5)
        self.usage_table.setHorizontalHeaderLabels(["Host", "Requests", "Upload", "Download", "Total"])
        self.usage_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.usage_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.usage_table.setStyleSheet("""
            QTableWidget { background-color: transparent; border: none; color: #e0e0e0; gridline-color: #333; }
            QHeaderView::section { background-color: #252525; color: #b0b0b0; padding: 5px; border: 1px solid #333; }
        """)
        table_layout.addWidget(self.usage_table)
        layout.addWidget(table_container)

        # History Chart Placeholder
        chart_container = QFrame()
        chart_container.setStyleSheet("background-color: #1e1e1e; border-radius: 10px; border: 1px solid #333;")
        chart_layout = QVBoxLayout(chart_container)
        chart_title = QLabel("Traffic History (Last 7 Days)")
        chart_title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        chart_layout.addWidget(chart_title)

        self.usage_chart = UsageChart()
        chart_layout.addWidget(self.usage_chart)

        self.history_summary = QLabel()
        self.history_summary.setStyleSheet("color: #b0b0b0; font-family: monospace;")
        chart_layout.addWidget(self.history_summary)

        layout.addWidget(chart_container)

        return page

    def _create_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QHBoxLayout()
        header_text = QLabel("Settings")
        header_text.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header_text.setStyleSheet("color: white;")
        header.addWidget(header_text)
        header.addStretch()

        btn_import = QPushButton("Import")
        btn_import.setIcon(qta.icon("fa5s.file-import", color="white"))
        btn_import.clicked.connect(self._import_config)
        header.addWidget(btn_import)

        btn_export = QPushButton("Export")
        btn_export.setIcon(qta.icon("fa5s.file-export", color="white"))
        btn_export.clicked.connect(self._export_config)
        header.addWidget(btn_export)

        layout.addLayout(header)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #333; background: #1e1e1e; border-radius: 5px; }
            QTabBar::tab { background: #252525; color: #b0b0b0; padding: 10px 20px; border-top-left-radius: 5px; border-top-right-radius: 5px; margin-right: 2px; }
            QTabBar::tab:selected { background: #1e1e1e; color: #3498db; border-bottom: 2px solid #3498db; }
        """)

        # Styles for Inputs
        input_style = """
            QLineEdit, QSpinBox, QDoubleSpinBox {
                background-color: #121212;
                color: #e0e0e0;
                border: 1px solid #333;
                padding: 8px;
                border-radius: 5px;
            }
            QCheckBox { color: #e0e0e0; }
        """
        label_style = "color: #b0b0b0;"

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
        if isinstance(script_ids, list):
            script_ids_text = "\n".join(script_ids)
        else:
            script_ids_text = str(script_ids)

        self.edit_script_id = QTextEdit()
        self.edit_script_id.setPlaceholderText("Enter one or more Apps Script IDs, one per line.")
        self.edit_script_id.setPlainText(script_ids_text)
        self.edit_script_id.setFixedHeight(100)
        self.edit_script_id.setStyleSheet(input_style)
        add_row(general_f, "Apps Script IDs:", self.edit_script_id)

        self.edit_auth_key = QLineEdit(self.config.get("auth_key", ""))
        self.edit_auth_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_auth_key.setStyleSheet(input_style)
        add_row(general_f, "Auth Key:", self.edit_auth_key)

        self.edit_google_ip = QLineEdit(self.config.get("google_ip", "216.239.38.120"))
        self.edit_google_ip.setStyleSheet(input_style)
        add_row(general_f, "Google Frontend IP:", self.edit_google_ip)

        self.edit_default_mode = QComboBox()
        self.edit_default_mode.addItems(["Relay", "Direct", "Block"])
        self.edit_default_mode.setCurrentText(self.config.get("default_connection_mode", "relay").capitalize())
        self.edit_default_mode.setStyleSheet("background-color: #121212; color: #e0e0e0; border: 1px solid #333; padding: 5px; border-radius: 5px;")
        add_row(general_f, "Default Connection Mode:", self.edit_default_mode)

        tabs.addTab(general_w, "General")

        # Tab 2: Network
        network_w, network_f = create_form_tab()
        self.edit_listen_port = QLineEdit(str(self.config.get("listen_port", 8085)))
        self.edit_listen_port.setStyleSheet(input_style)
        add_row(network_f, "HTTP Proxy Port:", self.edit_listen_port)

        self.edit_socks_port = QLineEdit(str(self.config.get("socks5_port", 1080)))
        self.edit_socks_port.setStyleSheet(input_style)
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
        self.spin_parallel.setStyleSheet(input_style)
        add_row(relay_f, "Parallel Relay Count:", self.spin_parallel)

        self.edit_bypass_hosts = QTextEdit()
        self.edit_bypass_hosts.setPlainText("\n".join(self.config.get("bypass_hosts", [])))
        self.edit_bypass_hosts.setStyleSheet("background-color: #121212; color: #e0e0e0; border: 1px solid #333; border-radius: 5px;")
        add_row(relay_f, "Bypass Hosts:", self.edit_bypass_hosts)

        tabs.addTab(relay_w, "Relay")

        layout.addWidget(tabs)

        self.restart_hint = QLabel("Note: Changes to ports or LAN sharing require a proxy restart.")
        self.restart_hint.setStyleSheet("color: #e67e22; font-size: 11px; margin-top: 5px;")
        self.restart_hint.setVisible(False)
        layout.addWidget(self.restart_hint)

        btn_save = QPushButton("Save Settings")
        btn_save.setFixedSize(150, 40)
        btn_save.setStyleSheet("background-color: #3498db; color: white; border-radius: 5px; font-weight: bold; margin-top: 10px;")
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

        script_ids_text = self.edit_script_id.toPlainText()
        script_ids = [s.strip() for s in script_ids_text.split("\n") if s.strip()]
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
                    if isinstance(script_ids, list):
                        self.edit_script_id.setPlainText("\n".join(script_ids))
                    else:
                        self.edit_script_id.setPlainText(str(script_ids))

                    self.edit_auth_key.setText(self.config.get("auth_key", ""))
                    self.edit_google_ip.setText(self.config.get("google_ip", ""))
                    self.edit_listen_port.setText(str(self.config.get("listen_port", 8085)))
                    self.edit_socks_port.setText(str(self.config.get("socks5_port", 1080)))
                    self.check_lan.setChecked(self.config.get("lan_sharing", False))
                    self.spin_parallel.setValue(self.config.get("parallel_relay", 1))
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

    window = ModernUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
