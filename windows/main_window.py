from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

class MainWindowTab(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.main_label = QLabel("Главное окно")
        self.main_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.main_label)
