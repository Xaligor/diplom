import os
import wakeonlan
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

def wake_on_lan(panel):
    parent = panel.parent
    mac_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            mac = parent.hosts_table.item(row, 4).text()
            mac_list.append(mac)

    if not mac_list:
        QMessageBox.information(parent, "Wake on LAN", "Нет выбранных хостов с MAC адресами.")
        return

    for mac in mac_list:
        wakeonlan.send_magic_packet(mac)
        QMessageBox.information(parent, "Wake on LAN", f"Команда Wake on LAN отправлена для MAC адреса {mac}.")

def reboot(panel):
    parent = panel.parent
    key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

    if not os.path.exists(key_path):
        QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
        return

    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = parent.hosts_table.item(row, 3).text()
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Перезагрузка", "Нет выбранных хостов.")
        return

    for host in host_list:
        try:
            parent.run_ssh_thread("reboot", host, key_path)
        except Exception as e:
            QMessageBox.critical(parent, "Ошибка", f"Произошла ошибка при перезагрузке хоста {host}: {str(e)}")

def shutdown(panel):
    parent = panel.parent
    key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

    if not os.path.exists(key_path):
        QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
        return

    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = parent.hosts_table.item(row, 3).text()
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Выключение", "Нет выбранных хостов.")
        return

    for host in host_list:
        try:
            parent.run_ssh_thread("shutdown", host, key_path)
        except Exception as e:
            QMessageBox.critical(parent, "Ошибка", f"Произошла ошибка при выключении хоста {host}: {str(e)}")
