import os
import paramiko
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, Qt

class SSHThread(QThread):
    result_signal = pyqtSignal(bool, str)

    def __init__(self, command, host, key_path, sftp_command=None):
        super().__init__()
        self.command = command
        self.host = host
        self.key_path = key_path
        self.sftp_command = sftp_command

    def run(self):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(self.host, username='root', key_filename=self.key_path)

            if self.sftp_command:
                sftp = ssh.open_sftp()
                sftp.put(*self.sftp_command)
                sftp.close()
            else:
                stdin, stdout, stderr = ssh.exec_command(self.command)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status != 0:
                    raise Exception(stderr.read().decode())

            ssh.close()
            self.result_signal.emit(True, self.host)
        except Exception as e:
            print(f"Error: {e}")
            self.result_signal.emit(False, self.host)

def install_veyon(panel):
    parent = panel.parent
    key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

    if not os.path.exists(key_path):
        QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
        return

    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if panel.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = panel.hosts_table.item(row, 3).text()
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Установка Veyon", "Нет выбранных хостов.")
        return

    veyon_settings_path = os.path.join(os.getcwd(), 'veyon', 'veyon_settings.json')
    school_public_key_path = os.path.join(os.getcwd(), 'veyon', 'school_public_key.pem')

    if not (os.path.exists(veyon_settings_path) and os.path.exists(school_public_key_path)):
        QMessageBox.warning(parent, "Ошибка", "Не найдены необходимые файлы для установки Veyon.")
        return

    for host in host_list:
        try:
            # Step 1: Install Veyon
            install_thread = SSHThread("dnf install -y veyon", host, key_path)
            install_thread.result_signal.connect(lambda success, h=host: handle_result(success, h, "установке Veyon"))
            install_thread.start()
            install_thread.wait()

            # Step 2: Apply Veyon settings
            scp_settings_thread = SSHThread(None, host, key_path, (veyon_settings_path, "/tmp/veyon_settings.json"))
            scp_settings_thread.result_signal.connect(lambda success, h=host: handle_result(success, h, "копировании настроек Veyon"))
            scp_settings_thread.start()
            scp_settings_thread.wait()

            apply_settings_thread = SSHThread("veyon-cli config import /tmp/veyon_settings.json", host, key_path)
            apply_settings_thread.result_signal.connect(lambda success, h=host: handle_result(success, h, "применении настроек Veyon"))
            apply_settings_thread.start()
            apply_settings_thread.wait()

            # Step 3: Import public key
            scp_key_thread = SSHThread(None, host, key_path, (school_public_key_path, "/tmp/school_public_key.pem"))
            scp_key_thread.result_signal.connect(lambda success, h=host: handle_result(success, h, "копировании ключа Veyon"))
            scp_key_thread.start()
            scp_key_thread.wait()

            import_key_thread = SSHThread("veyon-cli authkeys import school/public /tmp/school_public_key.pem", host, key_path)
            import_key_thread.result_signal.connect(lambda success, h=host: handle_result(success, h, "импорте ключа Veyon"))
            import_key_thread.start()
            import_key_thread.wait()

            QMessageBox.information(parent, "Установка Veyon", f"Установка Veyon на {host} завершена.")
        except Exception as e:
            QMessageBox.critical(parent, "Ошибка", f"Произошла ошибка при установке Veyon на хосте {host}: {str(e)}")

def apply_veyon_settings(panel):
    parent = panel.parent
    key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

    if not os.path.exists(key_path):
        QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
        return

    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if panel.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = panel.hosts_table.item(row, 3).text()
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Применение настроек Veyon", "Нет выбранных хостов.")
        return

    veyon_settings_path = os.path.join(os.getcwd(), 'veyon', 'veyon_settings.json')

    if not os.path.exists(veyon_settings_path):
        QMessageBox.warning(parent, "Ошибка", "Файл настроек veyon_settings.json не найден.")
        return

    for host in host_list:
        try:
            # Copy and apply Veyon settings
            scp_settings_thread = SSHThread(None, host, key_path, (veyon_settings_path, "/tmp/veyon_settings.json"))
            scp_settings_thread.result_signal.connect(lambda success, h=host: handle_result(success, h, "копировании настроек Veyon"))
            scp_settings_thread.start()
            scp_settings_thread.wait()

            apply_settings_thread = SSHThread("veyon-cli config import /tmp/veyon_settings.json", host, key_path)
            apply_settings_thread.result_signal.connect(lambda success, h=host: handle_result(success, h, "применении настроек Veyon"))
            apply_settings_thread.start()
            apply_settings_thread.wait()

            QMessageBox.information(parent, "Применение настроек Veyon", f"Настройки Veyon на {host} применены.")
        except Exception as e:
            QMessageBox.critical(parent, "Ошибка", f"Произошла ошибка при применении настроек Veyon на хосте {host}: {str(e)}")

def restart_veyon_service(panel):
    parent = panel.parent
    key_path = os.path.join(os.getcwd(), 'SSH', 'id_rsa')

    if not os.path.exists(key_path):
        QMessageBox.warning(parent, "Ошибка", "SSH ключи не найдены в папке 'SSH'.")
        return

    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if panel.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = panel.hosts_table.item(row, 3).text()
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Перезапуск службы Veyon", "Нет выбранных хостов.")
        return

    for host in host_list:
        try:
            restart_thread = SSHThread("systemctl restart veyon.service", host, key_path)
            restart_thread.result_signal.connect(lambda success, h=host: handle_result(success, h, "перезапуске службы Veyon"))
            restart_thread.start()
            restart_thread.wait()

            QMessageBox.information(parent, "Перезапуск службы Veyon", f"Служба Veyon на {host} перезапущена.")
        except Exception as e:
            QMessageBox.critical(parent, "Ошибка", f"Произошла ошибка при перезапуске службы Veyon на хосте {host}: {str(e)}")

def handle_result(success, host, operation):
    if success:
        print(f"Успешно: {operation} на хосте {host}")
    else:
        print(f"Неудачно: {operation} на хосте {host}")

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
        ssh.connect(host, username='root', key_filename=os.path.join(os.getcwd(), 'SSH', 'id_rsa'))
        ssh.close()
        return True
    except Exception as e:
        print(f"SSH test failed for {host}: {str(e)}")
        return False
