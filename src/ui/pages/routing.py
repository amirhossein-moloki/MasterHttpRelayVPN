import logging
import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QDialog, QFormLayout, QLineEdit,
    QComboBox, QDialogButtonBox, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
import qtawesome as qta
from ..styles import COLORS

class RoutingPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_win = main_window
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()
        header = QLabel("Routing Rules")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['text_main']}; letter-spacing: -1px;")
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

    def _refresh_routing_table(self):
        groups = self.main_win.config.get("rule_groups") or self.main_win.config.get("bypass_groups") or []
        self.routing_table.setRowCount(len(groups))

        for i, group in enumerate(groups):
            check_widget = QWidget()
            check_layout = QHBoxLayout(check_widget)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb = QCheckBox()
            cb.setChecked(group.get("enabled", True))
            cb.stateChanged.connect(lambda state, idx=i: self._toggle_group_enabled(idx, state))
            check_layout.addWidget(cb)
            self.routing_table.setCellWidget(i, 0, check_widget)

            self.routing_table.setItem(i, 1, QTableWidgetItem(group.get("name", "Unnamed")))

            mode = group.get("mode", "direct").upper()
            mode_item = QTableWidgetItem(mode)
            if mode == "RELAY": mode_item.setForeground(QColor("#3498db"))
            elif mode == "DIRECT": mode_item.setForeground(QColor("#2ecc71"))
            elif mode == "BLOCK": mode_item.setForeground(QColor("#e74c3c"))
            self.routing_table.setItem(i, 2, mode_item)

            rules = group.get("rules", [])
            url = group.get("update_url", "")
            if url:
                summary = f"Subscription: {url[:30]}..."
            else:
                summary = f"{len(rules)} items: {', '.join(rules[:3])}"
                if len(rules) > 3: summary += "..."
            self.routing_table.setItem(i, 3, QTableWidgetItem(summary))

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
            btn_del.setIcon(qta.icon("fa5s.trash-alt", color=COLORS['danger']))
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

            if "rule_groups" not in self.main_win.config:
                self.main_win.config["rule_groups"] = self.main_win.config.get("bypass_groups", [])
                if "bypass_groups" in self.main_win.config: del self.main_win.config["bypass_groups"]

            group_name = f"General {mode.capitalize()} Rules"
            target_group = None
            for g in self.main_win.config.get("rule_groups", []):
                if g["name"] == group_name and g["mode"] == mode and not g.get("update_url"):
                    target_group = g
                    break

            if not target_group:
                target_group = {"name": group_name, "enabled": True, "mode": mode, "rules": [], "update_url": ""}
                if "rule_groups" not in self.main_win.config: self.main_win.config["rule_groups"] = []
                self.main_win.config["rule_groups"].append(target_group)

            if host not in target_group["rules"]:
                target_group["rules"].append(host)
                self.main_win._save_config()
                self.main_win.proxy_service.update_config(self.main_win.config)
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
            if "rule_groups" not in self.main_win.config:
                self.main_win.config["rule_groups"] = self.main_win.config.get("bypass_groups", [])
                if "bypass_groups" in self.main_win.config: del self.main_win.config["bypass_groups"]

            self.main_win.config["rule_groups"].append({
                "name": name, "enabled": True, "mode": edit_mode.currentText().lower(), "rules": [], "update_url": ""
            })
            self.main_win._save_config()
            self.main_win.proxy_service.update_config(self.main_win.config)
            self._refresh_routing_table()

    def _toggle_group_enabled(self, index, state):
        groups = self.main_win.config.get("rule_groups") or self.main_win.config.get("bypass_groups") or []
        if 0 <= index < len(groups):
            groups[index]["enabled"] = (state == Qt.CheckState.Checked.value)
            self.main_win._save_config()
            self.main_win.proxy_service.update_config(self.main_win.config)

    def _edit_routing_ruleset(self, index):
        groups = self.main_win.config.get("rule_groups") or self.main_win.config.get("bypass_groups") or []
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
                if "bypass_groups" in self.main_win.config:
                    self.main_win.config["rule_groups"] = groups
                    del self.main_win.config["bypass_groups"]
                self.main_win._save_config()
                self.main_win.proxy_service.update_config(self.main_win.config)
                self._refresh_routing_table()

    def _delete_routing_ruleset(self, index):
        ret = QMessageBox.question(self, "Delete Group", "Are you sure you want to delete this group?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ret == QMessageBox.StandardButton.Yes:
            groups = self.main_win.config.get("rule_groups") or self.main_win.config.get("bypass_groups") or []
            if 0 <= index < len(groups):
                groups.pop(index)
                if "bypass_groups" in self.main_win.config:
                    self.main_win.config["rule_groups"] = groups
                    del self.main_win.config["bypass_groups"]
                self.main_win._save_config()
                self.main_win.proxy_service.update_config(self.main_win.config)
                self._refresh_routing_table()

    def _update_group_rules(self, index):
        if not self.main_win.proxy_service.is_running:
            logging.warning("Start the proxy first to enable background updates.")
            return

        async def do_update():
            success = await self.main_win.proxy_service.update_bypass_group(index)
            if success:
                self.main_win._save_config()
                self.main_win.proxy_service.update_config(self.main_win.config)
                QTimer.singleShot(0, self._refresh_routing_table)
                logging.info(f"Group {index} updated successfully.")
            else:
                logging.error(f"Failed to update group {index}.")
        asyncio.run_coroutine_threadsafe(do_update(), self.main_win.proxy_service.loop)
