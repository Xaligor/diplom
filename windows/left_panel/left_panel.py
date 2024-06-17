import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import Qt
from .network_management import check_ping, setup_ssh, delete_ssh, get_ip_mac_addresses, setup_wol
from .power_management import wake_on_lan, reboot, shutdown
from .user_management import *
from .veyon_management import *
from .command_execution import run_root_command_on_ssh, install_programs, remove_programs
from .restrictions_management import restrict_desktop_change, restrict_network, password_protect

class LeftPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.hosts_table = parent.hosts_table
        self.layout = QVBoxLayout(self)

        self.treeview = QTreeWidget()
        self.treeview.setHeaderHidden(True)
        self.treeview.setIndentation(10)
        self.layout.addWidget(self.treeview)

        self.create_network_groupbox()
        self.create_power_management_groupbox()
        self.create_users_groupbox()
        self.create_veyon_groupbox()
        self.create_commands_groupbox()
        self.create_restrictions_groupbox()

    def create_groupbox(self, title, buttons):
        groupbox = QTreeWidgetItem(self.treeview)
        groupbox.setText(0, title)
        groupbox.setExpanded(False)
        for button in buttons:
            item = QTreeWidgetItem(groupbox)
            self.treeview.setItemWidget(item, 0, button)
        self.treeview.addTopLevelItem(groupbox)

    def create_network_groupbox(self):
        buttons = [
            self.create_button('Проверить ping', lambda: check_ping(self)),
            self.create_button('Настроить доступ по ssh', lambda: setup_ssh(self)),
            self.create_button('Удалить ключи ssh', lambda: delete_ssh(self)),
            self.create_button('Получить IP & MAC адреса', lambda: get_ip_mac_addresses(self)),
            self.create_button('Включить Wake on LAN', lambda: setup_wol(self))
        ]
        self.create_groupbox("Сеть", buttons)

    def create_power_management_groupbox(self):
        buttons = [
            self.create_button('Включить', lambda: wake_on_lan(self)),
            self.create_button('Перезагрузить', lambda: reboot(self)),
            self.create_button('Выключить', lambda: shutdown(self))
        ]
        self.create_groupbox("Управление питанием", buttons)

    def create_users_groupbox(self):
        buttons = [
            self.create_button('Создать учётные записи учеников', lambda: create_student(self)),
            self.create_button('Удалить учётные записи учеников', lambda: delete_student(self)),
            self.create_button('Включить автологин учеников', lambda: autologin_enable_func(self)),
            self.create_button('Выключить автологин учеников', lambda: autologin_disable_func(self))
        ]
        self.create_groupbox("Пользователи", buttons)

    from .veyon_management import install_veyon

    def create_veyon_groupbox(self):
        buttons = [
            self.create_button('Установить Veyon', lambda: install_veyon(self)),
            self.create_button('Применить настройки Veyon', lambda: apply_veyon_settings(self)),
            self.create_button('Перезапустить службу Veyon', lambda: restart_veyon_service(self))
        ]
        self.create_groupbox("Veyon", buttons)

    def create_commands_groupbox(self):
        buttons = [
            self.create_button('Выполнить команду от root', lambda: run_root_command_on_ssh(self)),
            self.create_button('Установить программы', lambda: install_programs(self)),
            self.create_button('Удалить программы', lambda: remove_programs(self))
        ]
        self.create_groupbox("Выполнение команд", buttons)

    def create_restrictions_groupbox(self):
        buttons = [
            self.create_button('Запретить изменения рабочего стола', lambda: restrict_desktop_change(self, True)),
            self.create_button('Разрешить изменения рабочего стола', lambda: restrict_desktop_change(self, False)),
            self.create_button('Отключить интернет на хостах', lambda: restrict_network(self, True)),
            self.create_button('Включить интернет на хостах', lambda: restrict_network(self, False)),
            self.create_button('Защитить настройки паролем', lambda: password_protect(self, True)),
            self.create_button('Снять защиту паролем', lambda: password_protect(self, False))
        ]
        self.create_groupbox("Ограничения профиля", buttons)

    def create_button(self, text, func):
        button = QPushButton(text)
        button.clicked.connect(func)
        return button
