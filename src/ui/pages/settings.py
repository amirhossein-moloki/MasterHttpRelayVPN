import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget,
    QFormLayout, QLineEdit, QComboBox, QCheckBox, QScrollArea, QSpinBox,
    QTextEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
import qtawesome as qta
from ..widgets.script_id_list import ScriptIdList
from ..styles import COLORS

class SettingsPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_win = main_window
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header = QHBoxLayout()
        header_text = QLabel("Settings")
        header_text.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header_text.setStyleSheet(f"color: {COLORS['text_main']}; letter-spacing: -1px;")
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
        script_ids = self.main_win.config.get("script_ids") or self.main_win.config.get("script_id", "")
        self.script_id_list = ScriptIdList()
        self.script_id_list.set_ids(script_ids)
        script_scroll = QScrollArea()
        script_scroll.setWidgetResizable(True)
        script_scroll.setWidget(self.script_id_list)
        script_scroll.setMinimumHeight(150)
        script_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        add_row(general_f, "Apps Script IDs:", script_scroll)
        self.edit_auth_key = QLineEdit(self.main_win.config.get("auth_key", ""))
        self.edit_auth_key.setEchoMode(QLineEdit.EchoMode.Password)
        add_row(general_f, "Auth Key:", self.edit_auth_key)
        self.edit_google_ip = QLineEdit(self.main_win.config.get("google_ip", "216.239.38.120"))
        add_row(general_f, "Google Frontend IP:", self.edit_google_ip)
        self.edit_default_mode = QComboBox()
        self.edit_default_mode.addItems(["Relay", "Direct", "Block"])
        self.edit_default_mode.setCurrentText(self.main_win.config.get("default_connection_mode", "relay").capitalize())
        add_row(general_f, "Default Connection Mode:", self.edit_default_mode)
        tabs.addTab(general_w, "General")

        # Tab 2: Network
        network_w, network_f = create_form_tab()
        self.edit_listen_port = QLineEdit(str(self.main_win.config.get("listen_port", 8085)))
        add_row(network_f, "HTTP Proxy Port:", self.edit_listen_port)
        self.edit_socks_port = QLineEdit(str(self.main_win.config.get("socks5_port", 1080)))
        add_row(network_f, "SOCKS5 Port:", self.edit_socks_port)
        self.check_lan = QCheckBox("Allow LAN connections")
        self.check_lan.setChecked(self.main_win.config.get("lan_sharing", False))
        add_row(network_f, "", self.check_lan)
        tabs.addTab(network_w, "Network")

        # Tab 3: Relay
        relay_w, relay_f = create_form_tab()
        self.spin_parallel = QSpinBox()
        self.spin_parallel.setRange(1, 10)
        self.spin_parallel.setValue(self.main_win.config.get("parallel_relay", 1))
        add_row(relay_f, "Parallel Relay Count:", self.spin_parallel)
        self.check_youtube_relay = QCheckBox("Route YouTube through Relay")
        self.check_youtube_relay.setChecked(self.main_win.config.get("youtube_via_relay", False))
        add_row(relay_f, "YouTube Relay:", self.check_youtube_relay)
        self.edit_bypass_hosts = QTextEdit()
        self.edit_bypass_hosts.setPlainText("\n".join(self.main_win.config.get("bypass_hosts", [])))
        add_row(relay_f, "Bypass Hosts:", self.edit_bypass_hosts)
        tabs.addTab(relay_w, "Relay")

        # Tab 4: Exit Node
        exit_node_w, exit_node_f = create_form_tab()
        exit_cfg = self.main_win.config.get("exit_node", {})
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
        add_row(exit_node_f, "Auth PSK:", self.edit_exit_psk)
        self.combo_exit_mode = QComboBox()
        self.combo_exit_mode.addItems(["Selective", "Full"])
        self.combo_exit_mode.setCurrentText(exit_cfg.get("mode", "selective").capitalize())
        add_row(exit_node_f, "Routing Mode:", self.combo_exit_mode)
        self.edit_exit_hosts = QTextEdit()
        self.edit_exit_hosts.setPlainText("\n".join(exit_cfg.get("hosts", [])))
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

    def _save_settings_from_ui(self):
        self.restart_hint.setVisible(True)
        script_ids = self.script_id_list.get_ids()
        if len(script_ids) == 1:
            self.main_win.config["script_id"] = script_ids[0]
            if "script_ids" in self.main_win.config: del self.main_win.config["script_ids"]
        elif len(script_ids) > 1:
            self.main_win.config["script_ids"] = script_ids
            if "script_id" in self.main_win.config: del self.main_win.config["script_id"]
        else:
            self.main_win.config["script_id"] = ""
            if "script_ids" in self.main_win.config: del self.main_win.config["script_ids"]

        self.main_win.config["auth_key"] = self.edit_auth_key.text()
        self.main_win.config["google_ip"] = self.edit_google_ip.text()
        self.main_win.config["default_connection_mode"] = self.edit_default_mode.currentText().lower()
        try:
            self.main_win.config["listen_port"] = int(self.edit_listen_port.text())
            self.main_win.config["socks5_port"] = int(self.edit_socks_port.text())
        except: pass
        self.main_win.config["lan_sharing"] = self.check_lan.isChecked()
        self.main_win.config["parallel_relay"] = self.spin_parallel.value()
        self.main_win.config["youtube_via_relay"] = self.check_youtube_relay.isChecked()

        if "exit_node" not in self.main_win.config: self.main_win.config["exit_node"] = {}
        self.main_win.config["exit_node"]["enabled"] = self.check_exit_enabled.isChecked()
        self.main_win.config["exit_node"]["provider"] = self.combo_exit_provider.currentText().lower()
        self.main_win.config["exit_node"]["url"] = self.edit_exit_url.text().strip()
        self.main_win.config["exit_node"]["psk"] = self.edit_exit_psk.text().strip()
        self.main_win.config["exit_node"]["mode"] = self.combo_exit_mode.currentText().lower()
        self.main_win.config["exit_node"]["hosts"] = [h.strip() for h in self.edit_exit_hosts.toPlainText().split("\n") if h.strip()]

        self.main_win.config["bypass_hosts"] = [h.strip() for h in self.edit_bypass_hosts.toPlainText().split("\n") if h.strip()]
        self.main_win.config["mode"] = "apps_script"
        self.main_win._save_config()
        self.main_win.proxy_service.update_config(self.main_win.config)

    def _import_config(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Config", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "r") as f:
                    new_config = json.load(f)
                    self.main_win.config.update(new_config)
                    self.main_win._save_config()
                    # Reload UI elements
                    script_ids = self.main_win.config.get("script_ids") or self.main_win.config.get("script_id", "")
                    self.script_id_list.set_ids(script_ids)
                    self.edit_auth_key.setText(self.main_win.config.get("auth_key", ""))
                    self.edit_google_ip.setText(self.main_win.config.get("google_ip", ""))
                    self.edit_listen_port.setText(str(self.main_win.config.get("listen_port", 8085)))
                    self.edit_socks_port.setText(str(self.main_win.config.get("socks5_port", 1080)))
                    self.check_lan.setChecked(self.main_win.config.get("lan_sharing", False))
                    self.spin_parallel.setValue(self.main_win.config.get("parallel_relay", 1))
                    self.check_youtube_relay.setChecked(self.main_win.config.get("youtube_via_relay", False))
                    exit_cfg = self.main_win.config.get("exit_node", {})
                    self.check_exit_enabled.setChecked(exit_cfg.get("enabled", False))
                    self.edit_exit_url.setText(exit_cfg.get("url", ""))
                    self.edit_exit_psk.setText(exit_cfg.get("psk", ""))
                    self.edit_exit_hosts.setPlainText("\n".join(exit_cfg.get("hosts", [])))
                    self.edit_bypass_hosts.setPlainText("\n".join(self.main_win.config.get("bypass_hosts", [])))
            except Exception as e: logging.error(f"Import failed: {e}")

    def _export_config(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Config", "config_preset.json", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "w") as f: json.dump(self.main_win.config, f, indent=2)
            except Exception as e: logging.error(f"Export failed: {e}")

    def _reformat_config(self):
        try:
            self._save_settings_from_ui()
            logging.info("Configuration reformatted and saved successfully.")
            QMessageBox.information(self, "Success", "Configuration reformatted and saved successfully.")
        except Exception as e: logging.error(f"Reformat failed: {e}"); QMessageBox.critical(self, "Error", f"Failed to reformat config: {e}")

from PyQt6.QtGui import QFont
import json
