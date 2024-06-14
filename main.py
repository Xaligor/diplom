from PyQt5.QtWidgets import QMainWindow, QApplication, QTabWidget, QVBoxLayout, QWidget
from windows.main_window import MainWindowTab
from windows.diagnostics_window import DiagnosticsWindowTab
from windows.host_settings_window import HostSettingsWindowTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setMinimumWidth(700)
        self.setMinimumHeight(700)
        version = "1.0"
        self.setWindowTitle(f'Системы управления компьютерным классом с использованием Python на Linux, версия {version}')

        self.central_widget = QWidget()
        self.central_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        self.tabs = QTabWidget()
        self.central_layout.addWidget(self.tabs)

        self.main_window_tab = MainWindowTab()
        self.diagnostics_window_tab = DiagnosticsWindowTab()
        self.host_settings_window_tab = HostSettingsWindowTab()

        self.tabs.addTab(self.main_window_tab, "Основное окно")
        self.tabs.addTab(self.diagnostics_window_tab, "Диагностика")
        self.tabs.addTab(self.host_settings_window_tab, "Настройка хостов")

    def showEvent(self, event):
        super().showEvent(event)
        self.showMaximized()

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
