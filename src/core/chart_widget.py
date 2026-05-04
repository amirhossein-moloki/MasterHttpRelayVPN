from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

class SimpleChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.data = []  # List of (label, value)
        self.color = QColor("#3498db")

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        padding = 20
        chart_h = height - 2 * padding
        chart_w = width - 2 * padding

        max_val = max(v for _, v in self.data) if self.data else 1
        if max_val == 0: max_val = 1

        bar_w = (chart_w / len(self.data)) * 0.8
        spacing = (chart_w / len(self.data)) * 0.2

        for i, (label, val) in enumerate(self.data):
            bar_h = (val / max_val) * chart_h
            x = padding + i * (bar_w + spacing)
            y = height - padding - bar_h

            painter.setBrush(self.color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRect(int(x), int(y), int(bar_w), int(bar_h)), 3, 3)

            # Draw labels if enough space
            if len(self.data) < 15:
                painter.setPen(QColor("#b0b0b0"))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(QRect(int(x), height - padding + 2, int(bar_w), padding), Qt.AlignmentFlag.AlignCenter, label)
