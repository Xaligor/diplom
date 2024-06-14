import paramiko
import subprocess
import re
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QInputDialog, QLineEdit


class SSHManager:
    def __init__(self, host):
        self.host = host

    def run_command(self, command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Command failed with return code {result.returncode}")
                print(f"stderr: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            print(f"Error running command: {e}")
            return False

    def test_ssh(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host['hostname'], username='root', key_filename=os.path.join(os.getcwd(), 'SSH', 'id_rsa'))
            ssh.close()
            return True
        except Exception as e:
            print(f"SSH test failed for {self.host['hostname']}: {str(e)}")
            return False

    def check_student_on_host(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host['hostname'], username='root', key_filename=os.path.join(os.getcwd(), 'SSH', 'id_rsa'))
            stdin, stdout, stderr = ssh.exec_command(f"id -u {self.host['student_login']}")
            output = stdout.read().decode().strip()
            ssh.close()
            return output.isdigit()
        except Exception as e:
            print(f"Check student failed for {self.host['hostname']}: {str(e)}")
            return False

    def setup_ssh(self, password, replace_keys):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host['hostname'], username='root', password=password)
            sftp = ssh.open_sftp()
            key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')
            pub_key_path = f"{key_path}.pub"
            remote_key_paths = [
                "/home/teacher/.ssh/authorized_keys",
                "/root/.ssh/authorized_keys",
                "/etc/skel/.ssh/authorized_keys"
            ]

            for remote_key_path in remote_key_paths:
                try:
                    sftp.mkdir(os.path.dirname(remote_key_path), 0o700)
                except IOError:
                    pass

                if replace_keys:
                    sftp.put(pub_key_path, remote_key_path)
                else:
                    with sftp.open(remote_key_path, 'a') as f:
                        with open(pub_key_path, 'r') as pub_key_file:
                            f.write(pub_key_file.read())

                sftp.chmod(remote_key_path, 0o600)

            sftp.close()
            ssh.close()
            return True
        except Exception as e:
            print(f"Error setting up SSH on {self.host['hostname']}: {e}")
            return False

def check_ping(parent):
    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = {
                "name": parent.hosts_table.item(row, 2).text(),
                "hostname": parent.hosts_table.item(row, 3).text()
            }
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Ping", "Нет выбранных хостов.")
        return

    results = []
    for host in host_list:
        hostname = host['hostname']
        computer_name = host['name']
        response = subprocess.run(["ping", "-c", "1", hostname], capture_output=True, text=True)
        if response.returncode == 0:
            results.append(f"Компьютер: {computer_name} (Хост: {hostname})\nДоступен")
        else:
            results.append(f"Компьютер: {computer_name} (Хост: {hostname})\nНедоступен")
    QMessageBox.information(parent, "Результаты Ping", "\n\n".join(results))

def setup_ssh(parent):
    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = {
                "name": parent.hosts_table.item(row, 2).text(),
                "hostname": parent.hosts_table.item(row, 3).text()
            }
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Настройка SSH", "Нет выбранных хостов.")
        return

    password, ok = QInputDialog.getText(parent, 'Пароль SSH', 'Введите пароль для пользователя root на хосте:', QLineEdit.Password)
    if not ok:
        return

    dlg = QMessageBox(parent)
    dlg.setWindowTitle("Замена ключей")
    dlg.setText("Заменить ключи на компьютерах? Ответ НЕТ позволит добавить ключи к существующим.")
    dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
    dlg.button(QMessageBox.Yes).setText('Да')
    dlg.button(QMessageBox.No).setText('Нет')
    dlg.button(QMessageBox.Cancel).setText('Отмена')
    dlg.setIcon(QMessageBox.Question)
    button = dlg.exec()

    replace_keys = None
    if button == QMessageBox.Yes:
        replace_keys = True
    elif button == QMessageBox.No:
        replace_keys = False
    else:
        return

    for host in host_list:
        ssh_manager = SSHManager(host)
        if ssh_manager.setup_ssh(password, replace_keys):
            update_ssh_status(parent, host, True)
        else:
            update_ssh_status(parent, host, False)

    QMessageBox.information(parent, "Настройка SSH", "Настройка SSH завершена")

def delete_ssh(parent):
    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = {
                "name": parent.hosts_table.item(row, 2).text(),
                "hostname": parent.hosts_table.item(row, 3).text()
            }
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Удаление SSH", "Нет выбранных хостов.")
        return

    key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

    for host in host_list:
        ssh_manager = SSHManager(host)
        if ssh_manager.test_ssh():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host['hostname'], username='root', key_filename=key_path)
            sftp = ssh.open_sftp()
            remote_key_paths = [
                "/home/teacher/.ssh/authorized_keys",
                "/root/.ssh/authorized_keys",
                "/etc/skel/.ssh/authorized_keys"
            ]
            for remote_key_path in remote_key_paths:
                try:
                    sftp.remove(remote_key_path)
                except IOError:
                    pass  # Файл не найден
            sftp.close()
            ssh.close()
            update_ssh_status(parent, host, False)

    QMessageBox.information(parent, "Удаление SSH", "Удаление SSH ключей завершено.")

def get_ip_mac_addresses(parent):
    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = {
                "name": parent.hosts_table.item(row, 2).text(),
                "hostname": parent.hosts_table.item(row, 3).text()
            }
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Получение IP и MAC", "Нет выбранных хостов.")
        return

    for host in host_list:
        ssh_manager = SSHManager(host)
        if ssh_manager.test_ssh():
            ip_address, mac_address = ssh_manager.get_ip_mac()
            if ip_address and mac_address:
                update_ip_mac_in_table(parent, host, ip_address, mac_address)

    QMessageBox.information(parent, "Получение IP и MAC", "Получение IP и MAC адресов завершено.")

def setup_wol(parent):
    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = {
                "name": parent.hosts_table.item(row, 2).text(),
                "hostname": parent.hosts_table.item(row, 3).text()
            }
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Настройка WoL", "Нет выбранных хостов.")
        return

    key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

    for host in host_list:
        ssh_manager = SSHManager(host)
        if ssh_manager.test_ssh():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host['hostname'], username='root', key_filename=key_path)
            ssh.exec_command('echo \'ACTION=="add", SUBSYSTEM=="net", NAME=="en*", RUN+="/usr/sbin/ethtool -s $name wol g"\' > /etc/udev/rules.d/81-wol.rules')
            ssh.exec_command('reboot')
            ssh.close()
            update_wol_status(parent, host, True)

    QMessageBox.information(parent, "Настройка WoL", "Настройка WoL завершена")

def update_ssh_status(parent, host, status):
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 3).text() == host['hostname']:
            parent.hosts_table.setItem(row, 10, QTableWidgetItem("true" if status else "false"))
            break

def update_wol_status(parent, host, status):
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 3).text() == host['hostname']:
            parent.hosts_table.setItem(row, 11, QTableWidgetItem("true" if status else "false"))
            break

def update_ip_mac_in_table(parent, host, ip_address, mac_address):
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 3).text() == host['hostname']:
            parent.hosts_table.setItem(row, 4, QTableWidgetItem(mac_address))
            parent.hosts_table.setItem(row, 5, QTableWidgetItem(ip_address))
            break
