import logging
from datetime import datetime, timedelta
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QProgressBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import qtawesome as qta
from ..styles import COLORS

class DashboardPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_win = main_window
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(32)

        header_layout = QHBoxLayout()
        header = QLabel("Dashboard")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['text_main']}; letter-spacing: -1px;")
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
        self.status_detail.setStyleSheet(f"color: {COLORS['text_main']}; margin-top: 8px;")
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
            vlabel.setStyleSheet(f"color: {COLORS['text_main']}; margin-top: 4px;")
            blayout.addWidget(vlabel)
            return box, vlabel

        self.stat_box_1, self.val_requests = create_stat_box("Requests", "0", "fa5s.exchange-alt", COLORS['primary'])
        self.stat_box_2, self.val_data = create_stat_box("Bandwidth", "0 MB", "fa5s.database", COLORS['success'])
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

        script_ids = self.main_win.config.get("script_ids") or self.main_win.config.get("script_id")
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

    def _toggle_proxy(self):
        if self.main_win.proxy_service.is_running:
            self.main_win.proxy_service.stop()
        else:
            self.main_win.settings_page._save_settings_from_ui()
            self.main_win.proxy_service.config = self.main_win.config
            self.main_win.proxy_service.start()

    def update_status(self, status):
        if status == "starting":
            self.status_label.setText("STARTING...")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#f1c40f").pixmap(14, 14))
            self.toggle_btn.setEnabled(False)
        elif status == "stopped":
            self.status_label.setText("DISCONNECTED")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#444").pixmap(14, 14))
            self.toggle_btn.setText("Start Proxy")
            self.toggle_btn.setObjectName("PrimaryAction")
            self.toggle_btn.setStyle(self.toggle_btn.style())
            self.toggle_btn.setEnabled(True)
            self.status_detail.setText("Ready to secure your connection")
        elif "error" in status:
            self.status_label.setText("ERROR")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color="#e74c3c").pixmap(14, 14))
            self.status_detail.setText(status)
            self.toggle_btn.setText("Start Proxy")
            self.toggle_btn.setEnabled(True)
        else:
            self.status_label.setText("CONNECTED")
            self.status_label.setStyleSheet(f"color: {COLORS['success']}; letter-spacing: 1px;")
            self.status_icon.setPixmap(qta.icon("fa5s.circle", color=COLORS['success']).pixmap(14, 14))
            self.toggle_btn.setText("Stop Proxy")
            self.toggle_btn.setObjectName("StopAction")
            self.toggle_btn.setStyle(self.toggle_btn.style())
            self.toggle_btn.setEnabled(True)
            self.status_detail.setText(f"Listening on port {self.main_win.config.get('listen_port')}")

    def refresh_stats(self):
        # Implementation from gui.py _update_stats_impl that affects dashboard
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

        usage = self.main_win.proxy_service.get_usage(days=1)
        if usage:
            self.quota_label.setText(f"{usage['count']} / {usage['limit']}")
            self.quota_progress.setMaximum(usage['limit'])
            self.quota_progress.setValue(usage['count'])
            # Progress bar color logic
            if usage['percent'] > 90:
                self.quota_progress.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
            elif usage['percent'] > 70:
                self.quota_progress.setStyleSheet("QProgressBar::chunk { background-color: #f1c40f; }")
            else:
                self.quota_progress.setStyleSheet(f"QProgressBar::chunk {{ background-color: {COLORS['primary']}; }}")

        # Relay Health
        stats = self.main_win.proxy_service.get_stats()
        if stats:
            blacklisted = stats.get("blacklisted_scripts", [])
            script_ids = self.main_win.config.get("script_ids") or self.main_win.config.get("script_id")
            if not isinstance(script_ids, list): script_ids = [script_ids] if script_ids else []
            health_text = []
            for sid in script_ids:
                short_id = sid[-8:] if len(sid) > 8 else sid
                is_blacklisted = any(b['sid'] == sid[-12:] or b['sid'] == sid for b in blacklisted)
                if is_blacklisted:
                    health_text.append(f"<span style='color: #e74c3c;'>✖ {short_id} (Failing)</span>")
                else:
                    health_text.append(f"<span style='color: #2ecc71;'>✔ {short_id} (Healthy)</span>")
            self.health_list.setText("<br>".join(health_text) if health_text else "No scripts configured")

        # Total Stats
        total_usage = self.main_win.proxy_service.get_total_usage()
        if total_usage:
            self.val_requests.setText(str(total_usage['total_requests']))
            self.val_data.setText(f"{total_usage['total_bytes'] / (1024*1024):.1f} MB")

        # Latency
        if stats:
            total_req = sum(s['requests'] for s in stats['per_site'])
            if total_req > 0:
                avg_latency = sum(s['avg_ms'] * s['requests'] for s in stats['per_site']) / total_req
                self.val_latency.setText(f"{avg_latency:.0f} ms")
