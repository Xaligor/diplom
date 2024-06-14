import logging
from base64 import b64encode

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QInputDialog, QLineEdit, QMessageBox, QTableWidgetItem
from .network_management import SSHManager, update_ssh_status, update_wol_status, update_ip_mac_in_table

def create_student(parent):
    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = {
                "name": parent.hosts_table.item(row, 2).text(),
                "hostname": parent.hosts_table.item(row, 3).text(),
                "student_login": parent.hosts_table.item(row, 6).text(),
                "student_pass": parent.hosts_table.item(row, 7).text()
            }
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Создание учеников", "Нет выбранных хостов.")
        return

    for host in host_list:
        ssh_manager = SSHManager(host)
        if ssh_manager.test_ssh():
            if ssh_manager.check_student_on_host():
                logging.info(f'На {host["name"]} уже существует {host["student_login"]}')
                QMessageBox.information(parent, "Создание учеников", f'На {host["name"]} уже существует {host["student_login"]}')
            else:
                student_pass_bytes = host["student_pass"].encode('ascii')
                student_pass_base64_bytes = b64encode(student_pass_bytes)
                student_pass_base64_message = student_pass_base64_bytes.decode('ascii')
                command = (
                    f'useradd {host["student_login"]} && '
                    f'echo {host["student_login"]}:$(echo {student_pass_base64_message} | base64 -d) | chpasswd && '
                    f'reboot'
                )
                full_command = f'ssh root@{host["hostname"]} "echo \'{command}\' | at now"'

                if ssh_manager.run_command(full_command):
                    logging.info(f'На {host["name"]} создан {host["student_login"]}')
                    QMessageBox.information(parent, "Создание учеников", f'На {host["name"]} создан {host["student_login"]}')
                else:
                    logging.error(f'Ошибка при выполнении команды на {host["name"]}')
                    QMessageBox.information(parent, "Создание учеников", f'Ошибка при выполнении команды на {host["name"]}')
        else:
            logging.info(f'{host["name"]} не в сети или не настроен ssh')
            QMessageBox.information(parent, "Создание учеников", f'{host["name"]} не в сети или не настроен ssh')

def delete_student(parent):
    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = {
                "name": parent.hosts_table.item(row, 2).text(),
                "hostname": parent.hosts_table.item(row, 3).text(),
                "student_login": parent.hosts_table.item(row, 6).text()
            }
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Удаление учеников", "Нет выбранных хостов.")
        return

    for host in host_list:
        ssh_manager = SSHManager(host)
        if ssh_manager.test_ssh():
            if ssh_manager.check_student_on_host():
                if ssh_manager.run_command(
                        f'ssh root@{host["hostname"]} "py-ini-config del /etc/sddm.conf '
                        f'Autologin User --flush"'):
                    logging.info(f'Автологин студента на {host["hostname"]} выключен')
                    command = (
                        f'pkill -u {host["student_login"]} ; '
                        f'sleep 2 ; '
                        f'userdel -rf {host["student_login"]} ; '
                        f'reboot'
                    )
                    full_command = f'ssh root@{host["hostname"]} "echo \'{command}\' | at now"'

                    if ssh_manager.run_command(full_command):
                        logging.info(f'{host["name"]} {host["student_login"]} удален')
                        QMessageBox.information(parent, "Удаление учеников", f'{host["name"]} {host["student_login"]} удален')
                    else:
                        logging.error(f'Ошибка при выполнении команды на {host["name"]}')
                        QMessageBox.information(parent, "Удаление учеников", f'Ошибка при выполнении команды на {host["name"]}')
                else:
                    logging.error(f'Ошибка при выключении автологина на {host["name"]}')
                    QMessageBox.information(parent, "Удаление учеников", f'Ошибка при выключении автологина на {host["name"]}')
            else:
                logging.info(f'{host["name"]} отсутствует учётная запись ученика')
                QMessageBox.information(parent, "Удаление учеников", f'{host["name"]} отсутствует учётная запись ученика')
        else:
            logging.info(f'{host["name"]} не в сети или не настроен ssh')
            QMessageBox.information(parent, "Удаление учеников", f'{host["name"]} не в сети или не настроен ssh')

def autologin_enable_func(parent):
    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = {
                "name": parent.hosts_table.item(row, 2).text(),
                "hostname": parent.hosts_table.item(row, 3).text(),
                "student_login": parent.hosts_table.item(row, 6).text(),
            }
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Включение автологина", "Нет выбранных хостов.")
        return

    for host in host_list:
        ssh_manager = SSHManager(host)
        if ssh_manager.test_ssh():
            if not ssh_manager.check_student_on_host():
                QMessageBox.information(parent, "Включение автологина", f'На {host["name"]} нет учётной записи {host["student_login"]}.')
                continue

            command = f'py-ini-config set /etc/sddm.conf Autologin User {host["student_login"]}'
            full_command = f'ssh root@{host["hostname"]} "{command}"'

            if ssh_manager.run_command(full_command):
                QMessageBox.information(parent, "Включение автологина", f'Автологин {host["student_login"]} на {
host["name"]} включён')
            else:
                QMessageBox.information(parent, "Включение автологина", f'Ошибка при выполнении команды на {host["name"]}')
                logging.error(f'Ошибка при выполнении команды на {host["name"]}')
        else:
            QMessageBox.information(parent, "Включение автологина", f'{host["name"]} не в сети или не настроен ssh')
            logging.info(f'{host["name"]} не в сети или не настроен ssh')

def autologin_disable_func(parent):
    host_list = []
    for row in range(parent.hosts_table.rowCount()):
        if parent.hosts_table.item(row, 0).checkState() == Qt.Checked:
            host = {
                "name": parent.hosts_table.item(row, 2).text(),
                "hostname": parent.hosts_table.item(row, 3).text(),
                "student_login": parent.hosts_table.item(row, 6).text(),
            }
            host_list.append(host)

    if not host_list:
        QMessageBox.information(parent, "Выключение автологина", "Нет выбранных хостов.")
        return

    for host in host_list:
        ssh_manager = SSHManager(host)
        if ssh_manager.test_ssh():
            if not ssh_manager.check_student_on_host():
                QMessageBox.information(parent, "Выключение автологина", f'На {host["name"]} нет учётной записи {host["student_login"]}.')
                continue

            command = f'py-ini-config del /etc/sddm.conf Autologin User --flush'
            full_command = f'ssh root@{host["hostname"]} "{command}"'

            if ssh_manager.run_command(full_command):
                QMessageBox.information(parent, "Выключение автологина", f'Автологин {host["student_login"]} на {host["name"]} выключен')
            else:
                QMessageBox.information(parent, "Выключение автологина", f'Ошибка при выполнении команды на {host["name"]}')
                logging.error(f'Ошибка при выполнении команды на {host["name"]}')
        else:
            QMessageBox.information(parent, "Выключение автологина", f'{host["name"]} не в сети или не настроен ssh')
            logging.info(f'{host["name"]} не в сети или не настроен ssh')
