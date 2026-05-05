from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont

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
