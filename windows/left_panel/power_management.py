import os
import wakeonlan
import paramiko
from PyQt5.QtCore import Qt, QRunnable, QThreadPool, pyqtSlot, pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox

class WorkerSignals(QObject):
    result = pyqtSignal(bool, str)

class SSHWorker(QRunnable):
    def __init__(self, command, host, key_path):
        super().__init__()
        self.command = command
        self.host = host
        self.key_path = key_path
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, username='root', key_filename=self.key_path)
            stdin, stdout, stderr = ssh.exec_command(self.command)
            ssh.close()
            self.signals.result.emit(True, self.host)
        except Exception as e:
            print(f"Error: {e}")
            self.signals.result.emit(False, self.host)

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

    thread_pool = QThreadPool()
    for host in host_list:
        worker = SSHWorker("reboot", host, key_path)
        worker.signals.result.connect(lambda success, h=host: handle_result(success, h, "перезагрузке"))
        thread_pool.start(worker)

def shutdown(panel):
    parent = panel.parent
    key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

    if not os.path.exists(key_path):
        QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
        return

    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = panel.hosts_table.item(row, 3).text()
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Выключение", "Нет выбранных хостов.")
        return

    thread_pool = QThreadPool()
    for host in host_list:
        worker = SSHWorker("shutdown now", host, key_path)
        worker.signals.result.connect(lambda success, h=host: handle_result(success, h, "выключении"))
        thread_pool.start(worker)

def handle_result(success, host, operation):
    if success:
        print(f"Команда {operation} успешно отправлена на хост {host}")
    else:
        print(f"Команда {operation} не была успешно отправлена на хост {host}")
