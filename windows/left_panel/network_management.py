import paramiko
import subprocess
import re
import os
from PyQt5.QtWidgets import QMessageBox, QInputDialog, QLineEdit, QTableWidgetItem
from PyQt5.QtCore import QThread, pyqtSignal, Qt


class SSHThread(QThread):
    result_signal = pyqtSignal(bool, str, str, str)

    def __init__(self, command, host, key_path, extra=None):
        super().__init__()
        self.command = command
        self.host = host
        self.key_path = key_path
        self.extra = extra

    def run(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, username='root', key_filename=self.key_path)
            if self.command == "get_ip_mac":
                stdin, stdout, stderr = ssh.exec_command("ip addr show")
                output = stdout.read().decode()
                ip_address = self.parse_ip(output)
                mac_address = self.parse_mac(output)
                self.result_signal.emit(True, self.host, ip_address, mac_address)
            elif self.command == "setup_wol":
                stdin, stdout, stderr = ssh.exec_command('echo \'ACTION=="add", SUBSYSTEM=="net", NAME=="en*", RUN+="/usr/sbin/ethtool -s $name wol g"\' > /etc/udev/rules.d/81-wol.rules')
                ssh.exec_command('reboot')
                self.result_signal.emit(True, self.host, "", "")
            elif self.command == "reboot":
                ssh.exec_command('reboot')
                self.result_signal.emit(True, self.host, "", "")
            elif self.command == "shutdown":
                ssh.exec_command('shutdown now')
                self.result_signal.emit(True, self.host, "", "")
            elif self.command == "remove":
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
                self.result_signal.emit(True, self.host, "", "")
            else:
                self.result_signal.emit(False, self.host, "", "")
            ssh.close()
        except Exception as e:
            print(f"Error: {e}")
            self.result_signal.emit(False, self.host, "", "")

    def parse_ip(self, output):
        ip_pattern = re.compile(r'inet (\d+\.\d+\.\d+\.\d+)/\d+')
        matches = ip_pattern.findall(output)
        for ip in matches:
            if ip != "127.0.0.1":
                return ip
        return ""

    def parse_mac(self, output):
        mac_pattern = re.compile(r'link/ether ([0-9a-f:]+)')
        match = mac_pattern.search(output)
        if match:
            return match.group(1)
        return ""

def setup_ssh(panel) -> None:
    parent = panel.parent
    try:
        messageBox = QMessageBox.information(
            parent,
            "Важная информация!",
            "Вы запустили настройку ssh для пользователей root на компьютерах, указанных в таблице.\n\n"
            "Во время первичной настройки будет осуществляться подключение к компьютерам "
            "и сохранение ключей аутентификации для пользователя root.\n",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if messageBox == QMessageBox.Ok:
            key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')
            pub_key_path = f"{key_path}.pub"

            if not os.path.exists(key_path)  or not os.path.exists(pub_key_path):
                QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
                return

            host_list = []
            for row in range(panel.hosts_table.rowCount()):
                if panel.hosts_table.item(row, 0).checkState() == Qt.Checked:
                    host = panel.hosts_table.item(row, 3).text()
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

            successful_hosts = []
            for host in host_list:
                if configure_ssh(host, key_path, pub_key_path, password, replace_keys):
                    successful_hosts.append(host)

            for host in successful_hosts:
                update_ssh_status(panel, host, success=True)

            parent.save_to_folder()
            QMessageBox.information(parent, "Настройка SSH", "Настройка SSH завершена.")
    except Exception as e:
        print(f"Error in setup_ssh: {e}")

def configure_ssh(host, key_path, pub_key_path, password, replace_keys):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username='root', password=password)
        sftp = ssh.open_sftp()

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
    except paramiko.SSHException as e:
        print(f"SSHException: {e}")
        return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

def delete_ssh(panel) -> None:
    parent = panel.parent
    try:
        messageBox = QMessageBox.information(
            parent,
            "Важная информация!",
            "Вы запустили удаление ssh ключей на компьютерах, указанных в таблице.\n\n"
            "Будет выполнено подключение к компьютерам и удаление ключей аутентификации.\n",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if messageBox == QMessageBox.Ok:
            key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

            if not os.path.exists(key_path):
                QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
                return

            host_list = []
            for row in range(panel.hosts_table.rowCount()):
                if panel.hosts_table.item(row, 0).checkState() == Qt.Checked:
                    host = panel.hosts_table.item(row, 3).text()
                    host_list.append(host)

            if not host_list:
                QMessageBox.information(parent, "Удаление SSH", "Нет выбранных хостов.")
                return

            for host in host_list:
                parent.run_ssh_thread("remove", host, key_path)
    except Exception as e:
        print(f"Error in delete_ssh: {e}")

def check_ping(panel):
    parent = panel.parent
    try:
        selected_hosts = []
        for row in range(panel.hosts_table.rowCount()):
            if panel.hosts_table.item(row, 0).checkState() == Qt.Checked:
                hostname_item = panel.hosts_table.item(row, 3)
                computer_name_item = panel.hosts_table.item(row, 2)
                if hostname_item and computer_name_item:
                    selected_hosts.append((hostname_item.text(), computer_name_item.text()))

        if not selected_hosts:
            QMessageBox.information(parent, "Ping", "Нет выбранных хостов.")
            return

        results = []
        for host, computer_name in selected_hosts:
            if not host.strip():
                results.append(f"Компьютер: {computer_name}\nИмя хоста отсутствует.")
                continue

            try:
                response = subprocess.run(["ping", "-c", "1", host], capture_output=True, text=True, check=True)
                results.append(f"Компьютер: {computer_name} (Хост: {host})\nДоступен")
            except subprocess.CalledProcessError:
                results.append(f"Компьютер: {computer_name} (Хост: {host})\nНедоступен")

        if results:
            QMessageBox.information(parent, "Результаты Ping", "\n\n".join(results))
        else:
            QMessageBox.information(parent, "Ping", "Все выбранные хосты доступны.")
    except Exception as e:
        print(f"Error in check_ping: {e}")

def get_ip_mac_addresses(panel):
    parent = panel.parent
    try:
        key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

        if not os.path.exists(key_path):
            QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
            return

        host_list = []
        for row in range(panel.hosts_table.rowCount()):
            if panel.hosts_table.item(row, 0).checkState() == Qt.Checked:
                host = panel.hosts_table.item(row, 3).text()
                host_list.append(host)

        if not host_list:
            QMessageBox.information(parent, "Получение IP и MAC", "Нет выбранных хостов.")
            return

        for host in host_list:
            parent.run_ip_mac_thread("get_ip_mac", host, key_path)
    except Exception as e:
        print(f"Error in get_ip_mac_addresses: {e}")

def update_ssh_status(panel, host, success):
    try:
        for row in range(panel.hosts_table.rowCount()):
            if panel.hosts_table.item(row, 3).text() == host:
                panel.hosts_table.setItem(row, 10, QTableWidgetItem("True" if success else "False"))
                break
    except Exception as e:
        print(f"Error in update_ssh_status: {e}")

def update_wol_status(panel, host, success):
    try:
        for row in range(panel.hosts_table.rowCount()):
            if panel.hosts_table.item(row, 3).text() == host:
                panel.hosts_table.setItem(row, 11, QTableWidgetItem("True" if success else "False"))
                break
    except Exception as e:
        print(f"Error in update_wol_status: {e}")

def setup_wol(panel):
    parent = panel.parent
    try:
        key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

        if not os.path.exists(key_path):
            QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
            return

        host_list = []
        for row in range(panel.hosts_table.rowCount()):
            if panel.hosts_table.item(row, 0).checkState() == Qt.Checked:
                host = panel.hosts_table.item(row, 3).text()
                host_list.append(host)

        if not host_list:
            QMessageBox.information(parent, "Настройка WoL", "Нет выбранных хостов.")
            return

        for host in host_list:
            parent.run_ssh_thread("setup_wol", host, key_path)
    except Exception as e:
        print(f"Error in setup_wol: {e}")
def run_command(command):
    import subprocess
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Command failed with return code {result.returncode}")
            print(f"stderr: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}")
        return False

def test_ssh(host):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host['hostname'], username='root', key_filename=os.path.join(os.getcwd(), 'SSH', 'id_rsa'))
        ssh.close()
        return True
    except Exception as e:
        print(f"SSH test failed for {host['hostname']}: {str(e)}")
        return False

def check_student_on_host(host):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host['hostname'], username='root', key_filename=os.path.join(os.getcwd(), 'SSH', 'id_rsa'))
        stdin, stdout, stderr = ssh.exec_command(f"id -u {host['student_login']}")
        output = stdout.read().decode().strip()
        ssh.close()
        return output.isdigit()
    except Exception as e:
        print(f"Check student failed for {host['hostname']}: {str(e)}")
        return False