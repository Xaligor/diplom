import json
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QGridLayout, QPushButton, QFileDialog, QStyledItemDelegate,
    QHeaderView, QInputDialog, QLineEdit, QSplitter, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt
from .left_panel.left_panel import LeftPanel
from .left_panel.user_management import *

class PasswordDelegate(QStyledItemDelegate):
    def displayText(self, text, locale):
        return '*' * len(text)

class HostSettingsWindowTab(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)

        self.top_button_layout = QGridLayout()
        main_layout.addLayout(self.top_button_layout)
        self.create_top_buttons()

        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        self.hosts_table = QTableWidget()
        self.hosts_table.setColumnCount(14)
        self.hosts_table.setHorizontalHeaderLabels([
            "Выбор", "Кабинет", "Название", "Имя хоста", "MAC-адрес", "IP-адрес", "Логин ученика", "Пароль ученика",
            "Логин админа", "Пароль админа", "SSH", "WOL", "Veyon", "Remote Auth"
        ])
        self.hosts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        password_delegate = PasswordDelegate(self.hosts_table)
        self.hosts_table.setItemDelegateForColumn(7, password_delegate)
        self.hosts_table.setItemDelegateForColumn(9, password_delegate)

        main_splitter.addWidget(self.hosts_table)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)

        self.left_panel = LeftPanel(self)
        main_splitter.insertWidget(0, self.left_panel)

        self.load_from_json()

    def create_top_buttons(self):
        hosts_label = QLabel('Список устройств:')
        hosts_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.top_button_layout.addWidget(hosts_label, 0, 0)

        self.room_selector = QComboBox()
        self.room_selector.addItem("Все кабинеты")
        self.room_selector.currentTextChanged.connect(self.filter_by_room)
        self.top_button_layout.addWidget(self.room_selector, 0, 1)

        add_button = QPushButton('Добавить')
        add_button.clicked.connect(self.add_row)
        add_button.setToolTip('Добавить строку в таблицу')
        self.top_button_layout.addWidget(add_button, 0, 2)

        delete_button = QPushButton('Удалить')
        delete_button.clicked.connect(self.delete_row)
        delete_button.setToolTip('Удалить текущую строку в таблице')
        self.top_button_layout.addWidget(delete_button, 0, 3)

        generate_admins_btn = QPushButton('Генерация админов')
        generate_admins_btn.clicked.connect(self.generate_admins)
        generate_admins_btn.setToolTip('Генерация данных для админов')
        self.top_button_layout.addWidget(generate_admins_btn, 0, 4)

        generate_users_btn = QPushButton('Генерация пользователей')
        generate_users_btn.clicked.connect(self.generate_users)
        generate_users_btn.setToolTip('Генерация данных для пользователей')
        self.top_button_layout.addWidget(generate_users_btn, 0, 5)

        save_button = QPushButton('Сохранить')
        save_button.clicked.connect(self.save_to_folder)
        save_button.setToolTip('Сохранить таблицу в папку save')
        self.top_button_layout.addWidget(save_button, 0, 6)

        export_button = QPushButton('Экспорт')
        export_button.clicked.connect(self.export_to_json)
        export_button.setToolTip('Экспортировать данные из таблицы в JSON-файл')
        self.top_button_layout.addWidget(export_button, 0, 7)

        import_button = QPushButton('Импорт')
        import_button.clicked.connect(self.import_from_json)
        import_button.setToolTip('Импортировать данные из JSON-файла')
        self.top_button_layout.addWidget(import_button, 0, 8)

    def add_row(self):
        row_position = self.hosts_table.rowCount()
        self.hosts_table.insertRow(row_position)
        checkbox_item = QTableWidgetItem()
        checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        checkbox_item.setCheckState(Qt.Unchecked)
        self.hosts_table.setItem(row_position, 0, checkbox_item)

        default_values = [
            "", "Введите название", "", "", "", "",
            "", "", "false", "false", "false", "false", "false"
        ]
        for col, value in enumerate(default_values, start=1):
            self.hosts_table.setItem(row_position, col, QTableWidgetItem(value))

    def delete_row(self):
        rows_to_delete = []
        for row in range(self.hosts_table.rowCount()):
            if self.hosts_table.item(row, 0).checkState() == Qt.Checked:
                rows_to_delete.append(row)
        for row in reversed(rows_to_delete):
            self.hosts_table.removeRow(row)

    def save_to_folder(self):
        save_path = os.path.join(os.getcwd(), 'save', 'hosts_table.json')
        data = self.get_table_data()
        with open(save_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)

    def export_to_json(self):
        save_path = QFileDialog.getSaveFileName(self, "Экспортировать в JSON", "", "JSON Files (*.json)")[0]
        if save_path:
            data = self.get_table_data()
            with open(save_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

    def import_from_json(self):
        import_path = QFileDialog.getOpenFileName(self, "Импортировать из JSON", "", "JSON Files (*.json)")[0]
        if import_path:
            with open(import_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.hosts_table.setRowCount(0)
                for row_data in data:
                    row_position = self.hosts_table.rowCount()
                    self.hosts_table.insertRow(row_position)
                    checkbox_item = QTableWidgetItem()
                    checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    checkbox_item.setCheckState(Qt.Unchecked)
                    self.hosts_table.setItem(row_position, 0, checkbox_item)
                    for col, key in enumerate(row_data):
                        self.hosts_table.setItem(row_position, col + 1, QTableWidgetItem(row_data[key]))

                self.update_room_selector()

    def load_from_json(self):
        load_path = os.path.join(os.getcwd(), 'save', 'hosts_table.json')
        if os.path.exists(load_path):
            with open(load_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.hosts_table.setRowCount(0)
                for row_data in data:
                    row_position = self.hosts_table.rowCount()
                    self.hosts_table.insertRow(row_position)
                    checkbox_item = QTableWidgetItem()
                    checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    checkbox_item.setCheckState(Qt.Unchecked)
                    self.hosts_table.setItem(row_position, 0, checkbox_item)
                    for col, key in enumerate(row_data):
                        self.hosts_table.setItem(row_position, col + 1, QTableWidgetItem(row_data[key]))

                self.update_room_selector()

    def get_table_data(self):
        rows = self.hosts_table.rowCount()
        cols = self.hosts_table.columnCount()
        data = []

        for row in range(rows):
            row_data = {}
            for col in range(1, cols):
                item = self.hosts_table.item(row, col)
                item_text = item.text() if item else ''
                row_data[self.hosts_table.horizontalHeaderItem(col).text()] = item_text
            data.append(row_data)
        return data

    def generate_admins(self):
        login, ok_login = QInputDialog.getText(self, 'Генерация админов', 'Введите логин:')
        if ok_login:
            password, ok_password = QInputDialog.getText(self, 'Генерация админов', 'Введите пароль:', QLineEdit.Password)
            if ok_password:
                for row in range(self.hosts_table.rowCount()):
                    if self.hosts_table.item(row, 0).checkState() == Qt.Checked:
                        self.hosts_table.setItem(row, 8, QTableWidgetItem(login))
                        self.hosts_table.setItem(row, 9, QTableWidgetItem(password))

    def generate_users(self):
        login, ok_login = QInputDialog.getText(self, 'Генерация пользователей', 'Введите логин:')
        if ok_login:
            password, ok_password = QInputDialog.getText(self, 'Генерация пользователей', 'Введите пароль:', QLineEdit.Password)
            if ok_password:
                for row in range(self.hosts_table.rowCount()):
                    if self.hosts_table.item(row, 0).checkState() == Qt.Checked:
                        self.hosts_table.setItem(row, 6, QTableWidgetItem(login))
                        self.hosts_table.setItem(row, 7, QTableWidgetItem(password))

    def update_room_selector(self):
        rooms = set()
        for row in range(self.hosts_table.rowCount()):
            item = self.hosts_table.item(row, 1)
            if item and item.text():
                rooms.add(item.text())
        self.room_selector.clear()
        self.room_selector.addItem("Все кабинеты")
        self.room_selector.addItems(sorted(rooms))

    def filter_by_room(self, room):
        for row in range(self.hosts_table.rowCount()):
            item = self.hosts_table.item(row, 1)
            checkbox_item = self.hosts_table.item(row, 0)
            if room == "Все кабинеты":
                self.hosts_table.setRowHidden(row, False)
                checkbox_item.setCheckState(Qt.Unchecked)
            else:
                if item and item.text() == room:
                    self.hosts_table.setRowHidden(row, False)
                    checkbox_item.setCheckState(Qt.Checked)
                else:
                    self.hosts_table.setRowHidden(row, True)
                    checkbox_item.setCheckState(Qt.Unchecked)
