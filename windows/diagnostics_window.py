from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class DiagnosticsWindowTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.diagnostics_label = QLabel("Диагностика")
        self.diagnostics_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.diagnostics_label)
