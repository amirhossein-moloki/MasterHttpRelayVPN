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
        self.script_id_list = ScriptIdList()
        script_scroll = QScrollArea()
        script_scroll.setWidgetResizable(True)
        script_scroll.setWidget(self.script_id_list)
        script_scroll.setMinimumHeight(150)
        script_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        add_row(general_f, "Apps Script IDs:", script_scroll)
        self.edit_auth_key = QLineEdit()
        self.edit_auth_key.setEchoMode(QLineEdit.EchoMode.Password)
        add_row(general_f, "Auth Key:", self.edit_auth_key)
        self.edit_google_ip = QLineEdit()
        add_row(general_f, "Google Frontend IP:", self.edit_google_ip)
        self.edit_default_mode = QComboBox()
        self.edit_default_mode.addItems(["Relay", "Direct", "Block"])
        add_row(general_f, "Default Connection Mode:", self.edit_default_mode)
        tabs.addTab(general_w, "General")

        # Tab 2: Network
        network_w, network_f = create_form_tab()
        self.edit_listen_port = QLineEdit()
        add_row(network_f, "HTTP Proxy Port:", self.edit_listen_port)
        self.edit_socks_port = QLineEdit()
        add_row(network_f, "SOCKS5 Port:", self.edit_socks_port)
        self.check_lan = QCheckBox("Allow LAN connections")
        add_row(network_f, "", self.check_lan)
        tabs.addTab(network_w, "Network")

        # Tab 3: Relay
        relay_w, relay_f = create_form_tab()
        self.spin_parallel = QSpinBox()
        self.spin_parallel.setRange(1, 10)
        add_row(relay_f, "Parallel Relay Count:", self.spin_parallel)
        self.check_youtube_relay = QCheckBox("Route YouTube through Relay")
        add_row(relay_f, "YouTube Relay:", self.check_youtube_relay)
        self.edit_bypass_hosts = QTextEdit()
        add_row(relay_f, "Bypass Hosts:", self.edit_bypass_hosts)
        tabs.addTab(relay_w, "Relay")

        # Tab 4: Exit Node
        exit_node_w, exit_node_f = create_form_tab()
        self.check_exit_enabled = QCheckBox("Enable Exit Node (Chain Relay)")
        add_row(exit_node_f, "Status:", self.check_exit_enabled)
        self.combo_exit_provider = QComboBox()
        self.provider_map = {"custom": "Custom", "valtown": "ValTown", "cloudflare": "Cloudflare", "deno": "Deno", "vps": "VPS"}
        self.combo_exit_provider.addItems(list(self.provider_map.values()))
        add_row(exit_node_f, "Provider:", self.combo_exit_provider)
        self.edit_exit_url = QLineEdit()
        self.edit_exit_url.setPlaceholderText("https://your-exit-node-url.com")
        add_row(exit_node_f, "Exit Node URL:", self.edit_exit_url)
        self.edit_exit_psk = QLineEdit()
        self.edit_exit_psk.setEchoMode(QLineEdit.EchoMode.Password)
        add_row(exit_node_f, "Auth PSK:", self.edit_exit_psk)
        self.combo_exit_mode = QComboBox()
        self.combo_exit_mode.addItems(["Selective", "Full"])
        add_row(exit_node_f, "Routing Mode:", self.combo_exit_mode)
        self.edit_exit_hosts = QTextEdit()
        add_row(exit_node_f, "Selective Hosts:", self.edit_exit_hosts)
        tabs.addTab(exit_node_w, "Exit Node")

        # Tab 5: Adblock
        adblock_w, adblock_f = create_form_tab()
        self.check_adblock_enabled = QCheckBox("Enable Adblock")
        add_row(adblock_f, "Status:", self.check_adblock_enabled)
        self.edit_adblock_urls = QTextEdit()
        self.edit_adblock_urls.setPlaceholderText("https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts")
        add_row(adblock_f, "Blocklist URLs:", self.edit_adblock_urls)
        tabs.addTab(adblock_w, "Adblock")

        # Tab 6: Advanced / Region
        region_w, region_f = create_form_tab()
        self.btn_bypass_iran = QPushButton("Add/Update Iran Direct Routing Rule")
        self.btn_bypass_iran.setObjectName("SecondaryAction")
        self.btn_bypass_iran.clicked.connect(self._add_iran_bypass)
        add_row(region_f, "Iran Bypass:", self.btn_bypass_iran)
        desc_iran = QLabel("Automatically adds a routing group to bypass all Iranian IP ranges (Direct connection).")
        desc_iran.setStyleSheet("color: #777; font-size: 11px;")
        region_f.addRow("", desc_iran)
        tabs.addTab(region_w, "Region")

        layout.addWidget(tabs)
        self.restart_hint = QLabel("Note: Changes to ports or LAN sharing require a proxy restart.")
        self.restart_hint.setStyleSheet("color: #e67e22; font-size: 11px; margin-top: 5px;")
        self.restart_hint.setVisible(False)
        layout.addWidget(self.restart_hint)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel Changes")
        btn_cancel.setMinimumWidth(140)
        btn_cancel.setObjectName("SecondaryAction")
        btn_cancel.clicked.connect(self._load_settings_into_ui)
        btn_layout.addWidget(btn_cancel)

        btn_save = QPushButton("Save Settings")
        btn_save.setMinimumWidth(160)
        btn_save.setObjectName("PrimaryAction")
        btn_save.clicked.connect(self._save_settings_from_ui)
        btn_layout.addWidget(btn_save)

        layout.addLayout(btn_layout)

        # Initialize UI with current config
        self._load_settings_into_ui()

    def _load_settings_into_ui(self):
        config = self.main_win.config
        script_ids = config.get("script_ids") or config.get("script_id", "")
        self.script_id_list.set_ids(script_ids)
        self.edit_auth_key.setText(config.get("auth_key", ""))
        self.edit_google_ip.setText(config.get("google_ip", "216.239.38.120"))
        self.edit_default_mode.setCurrentText(config.get("default_connection_mode", "relay").capitalize())

        self.edit_listen_port.setText(str(config.get("listen_port", 8085)))
        self.edit_socks_port.setText(str(config.get("socks5_port", 1080)))
        self.check_lan.setChecked(config.get("lan_sharing", False))

        self.spin_parallel.setValue(config.get("parallel_relay", 1))
        self.check_youtube_relay.setChecked(config.get("youtube_via_relay", False))
        self.edit_bypass_hosts.setPlainText("\n".join(config.get("bypass_hosts", [])))

        exit_cfg = config.get("exit_node", {})
        self.check_exit_enabled.setChecked(exit_cfg.get("enabled", False))
        provider_key = exit_cfg.get("provider", "custom").lower()
        self.combo_exit_provider.setCurrentText(self.provider_map.get(provider_key, "Custom"))
        self.edit_exit_url.setText(exit_cfg.get("url", ""))
        self.edit_exit_psk.setText(exit_cfg.get("psk", ""))
        self.combo_exit_mode.setCurrentText(exit_cfg.get("mode", "selective").capitalize())
        self.edit_exit_hosts.setPlainText("\n".join(exit_cfg.get("hosts", [])))

        self.check_adblock_enabled.setChecked(config.get("adblock_enabled", True))
        self.edit_adblock_urls.setPlainText("\n".join(config.get("adblock_lists", [])))

    def _save_settings_from_ui(self):
        reply = QMessageBox.question(
            self, "Confirm Save",
            "Are you sure you want to save these settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

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

        self.main_win.config["adblock_enabled"] = self.check_adblock_enabled.isChecked()
        self.main_win.config["adblock_lists"] = [u.strip() for u in self.edit_adblock_urls.toPlainText().split("\n") if u.strip()]

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
                    self.check_adblock_enabled.setChecked(self.main_win.config.get("adblock_enabled", True))
                    self.edit_adblock_urls.setPlainText("\n".join(self.main_win.config.get("adblock_lists", [])))
                    self.edit_bypass_hosts.setPlainText("\n".join(self.main_win.config.get("bypass_hosts", [])))
            except Exception as e: logging.error(f"Import failed: {e}")

    def _add_iran_bypass(self):
        IRAN_IP_URL = "https://raw.githubusercontent.com/herrbischoff/country-ip-blocks/master/ipv4/ir.txt"

        if "rule_groups" not in self.main_win.config:
            self.main_win.config["rule_groups"] = self.main_win.config.get("bypass_groups", [])
            if "bypass_groups" in self.main_win.config: del self.main_win.config["bypass_groups"]

        groups = self.main_win.config.get("rule_groups", [])

        # Check if already exists
        found = False
        for g in groups:
            if g.get("name") == "Iran Direct" or g.get("update_url") == IRAN_IP_URL:
                g["name"] = "Iran Direct"
                g["update_url"] = IRAN_IP_URL
                g["mode"] = "direct"
                g["enabled"] = True
                found = True
                break

        if not found:
            groups.append({
                "name": "Iran Direct",
                "enabled": True,
                "mode": "direct",
                "rules": [],
                "update_url": IRAN_IP_URL
            })

        self.main_win.config["rule_groups"] = groups
        self.main_win._save_config()
        self.main_win.proxy_service.update_config(self.main_win.config)

        # Trigger update if proxy is running
        if self.main_win.proxy_service.is_running:
            idx = len(groups) - 1
            if found:
                for i, g in enumerate(groups):
                    if g.get("name") == "Iran Direct":
                        idx = i
                        break

            async def do_update():
                await self.main_win.proxy_service.update_bypass_group(idx)
                self.main_win._save_config()
                self.main_win.proxy_service.update_config(self.main_win.config)
                logging.info("Iran IP list updated from subscription.")

            import asyncio
            asyncio.run_coroutine_threadsafe(do_update(), self.main_win.proxy_service.loop)

        QMessageBox.information(self, "Success", "Iran Direct routing group added/updated. The IP list will be downloaded automatically.")

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
