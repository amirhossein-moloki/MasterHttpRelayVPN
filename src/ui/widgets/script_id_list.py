from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal
import qtawesome as qta

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
