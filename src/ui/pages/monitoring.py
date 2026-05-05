from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ..widgets.chart import UsageChart
from ..styles import COLORS

class MonitoringPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_win = main_window
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(24)

        header_layout = QHBoxLayout()
        header = QLabel("Monitoring")
        header.setFont(QFont("Inter", 28, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {COLORS['text_main']}; letter-spacing: -1px;")
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

        # History Chart
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

    def refresh_stats(self):
        days_map = {"Last 24 Hours": 1, "Last 7 Days": 7, "Last 30 Days": 30}
        selected_range = self.time_range_combo.currentText()
        days = days_map.get(selected_range, 1)

        usage = self.main_win.proxy_service.get_usage(days=days)
        if usage:
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
