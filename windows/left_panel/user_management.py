import logging
from base64 import b64encode
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QInputDialog, QLineEdit, QMessageBox, QTableWidgetItem
from .network_management import run_command, test_ssh, check_student_on_host

class CreateStudentThread(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, host_list, parent=None):
        super().__init__(parent)
        self.host_list = host_list

    def run(self):
        hosts_count = len(self.host_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}<br>Создание учётной записи ученика начинается<br>"
        )
        fail = []
        for host in self.host_list:
            if test_ssh(host):
                if check_student_on_host(host):
                    self.progress_signal.emit(f'На {host["name"]} уже существует {host["student_login"]}')
                    logging.info(f'На {host["name"]} уже существует {host["student_login"]}')
                    fail.append(f'{host["name"]} ({host["hostname"]})')
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

                    if run_command(full_command):
                        self.progress_signal.emit(f'На {host["name"]} создан {host["student_login"]}')
                        logging.info(f'На {host["name"]} создан {host["student_login"]}')
                        success_count += 1
                    else:
                        self.progress_signal.emit(f'Ошибка при выполнении команды на {host["name"]}')
                        logging.error(f'Ошибка при выполнении команды на {host["name"]}')
                        fail.append(f'{host["name"]} ({host["hostname"]})')
            else:
                self.progress_signal.emit(f'{host["name"]}: не в сети или не настроен ssh')
                logging.info(f'{host["name"]} не в сети или не настроен ssh')
                fail.append(f'{host["name"]} ({host["hostname"]})')
        if success_count == 0:
            self.progress_signal.emit(f"<br>Cоздание учётных записей учеников не выполнено.")
        elif success_count < hosts_count:
            self.progress_signal.emit(
                f'<br>Cоздание учётных записей учеников завершено. Компьютеры будут перезагружены.<br>'
                f'<font color="red">Выполнено на {success_count} из {hosts_count} устройств.</font>')
            self.progress_signal.emit(f'<br>Не выполнено на устройствах: {", ".join(fail)}')
        else:
            self.progress_signal.emit(
                f'Cоздание учётных записей учеников завершено. Компьютеры будут перезагружены.<br>'
                f'Cоздано на {success_count} из {hosts_count} компьютеров.')
        self.finish_signal.emit(f'Внимание! Перед дальнейшей работой проверьте, что на вновь созданных '
                                f'учётных записях присутствует подключение к сети.')

class DeleteStudentThread(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, host_list, parent=None):
        super().__init__(parent)
        self.host_list = host_list

    def run(self):
        hosts_count = len(self.host_list)
        success_count = 0
        fail = []
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}\nУдаление учётных записей учеников начинается...\n"
        )
        for host in self.host_list:
            if test_ssh(host):
                if check_student_on_host(host):
                    if run_command(
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

                        if run_command(full_command):
                            self.progress_signal.emit(f'{host["name"]}: {host["student_login"]} удален')
                            logging.info(f'{host["name"]} {host["student_login"]} удален')
                            success_count += 1
                        else:
                            self.progress_signal.emit(f'Ошибка при выполнении команды на {host["name"]}')
                            logging.error(f'Ошибка при выполнении команды на {host["name"]}')
                            fail.append(f'{host["name"]} ({host["hostname"]})')
                    else:
                        self.progress_signal.emit(f'Ошибка при выключении автологина на {host["name"]}')
                        logging.error(f'Ошибка при выключении автологина на {host["name"]}')
                        fail.append(f'{host["name"]} ({host["hostname"]})')
                else:
                    self.progress_signal.emit(f'{host["name"]}: отсутствует учётная запись ученика')
                    logging.info(f'{host["name"]} отсутствует учётная запись ученика')
                    fail.append(f'{host["name"]} ({host["hostname"]})')
            else:
                self.progress_signal.emit(f'{host["name"]}: не в сети или не настроен ssh')
                logging.info(f'{host["name"]} не в сети или не настроен ssh')
                fail.append(f'{host["name"]} ({host["hostname"]})')
        if success_count == 0:
            self.finish_signal.emit(f"\nУдаление учётных записей учеников не выполнено.")
        elif success_count < hosts_count:
            self.finish_signal.emit(
                f'<br>Удаление учётных записей учеников завершено. Компьютеры будут перезагружены.<br>'
                f'<font color="red">Выполнено на {success_count} из {hosts_count} устройств.</font>')
            self.finish_signal.emit(f'<br>Не выполнено на устройствах: {", ".join(fail)}')
        else:
            self.finish_signal.emit(
                f'Удаление учётных записей учеников завершено. Компьютеры будут перезагружены.<br>'
                f'Удалено на {success_count} из {hosts_count} компьютеров.')

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

    thread = CreateStudentThread(host_list, parent)
    thread.start_signal.connect(lambda message: QMessageBox.information(parent, "Начало", message))
    thread.progress_signal.connect(lambda message: QMessageBox.information(parent, "Прогресс", message))
    thread.finish_signal.connect(lambda message: QMessageBox.information(parent, "Завершение", message))
    thread.start()

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

    thread = DeleteStudentThread(host_list, parent)
    thread.start_signal.connect(lambda message: QMessageBox.information(parent, "Начало", message))
    thread.progress_signal.connect(lambda message: QMessageBox.information(parent, "Прогресс", message))
    thread.finish_signal.connect(lambda message: QMessageBox.information(parent, "Завершение", message))
    thread.start()

class AutologinThread(QThread):
    start_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(str)
    finish_signal = pyqtSignal(str)

    def __init__(self, host_list, turn_autologin_on, parent=None):
        super().__init__(parent)
        self.host_list = host_list
        self.turn_autologin_on = turn_autologin_on

    def run(self):
        hosts_count = len(self.host_list)
        success_count = 0
        self.start_signal.emit(
            f"Выбрано компьютеров: {hosts_count}<br>"
            f"{'Включение' if self.turn_autologin_on else 'Выключение'} автологина ученика начинается<br>"
        )
        fail = []
        for host in self.host_list:
            if test_ssh(host):
                if not check_student_on_host(host):
                    self.progress_signal.emit(f'На {host["name"]} нет учётной записи {host["student_login"]}.')
                    fail.append(f'{host["name"]} ({host["hostname"]})')
                    continue
                self.progress_signal.emit(f"{'Включение' if self.turn_autologin_on else 'Выключение'} "
                                          f"автологина {host['student_login']} на {host['name']}...")
                if self.turn_autologin_on:
                    command = f'py-ini-config set /etc/sddm.conf Autologin User {host["student_login"]}'
                else:
                    command = f'py-ini-config del /etc/sddm.conf Autologin User --flush'
                full_command = f'ssh root@{host["hostname"]} "{command}"'

                if run_command(full_command):
                    self.progress_signal.emit(f'Автологин {host["student_login"]} на {host["name"]} '
                                              f'{"включён" if self.turn_autologin_on else "выключен"}')
                    success_count += 1
                else:
                    self.progress_signal.emit(f'Ошибка при выполнении команды на {host["name"]}')
                    logging.error(f'Ошибка при выполнении команды на {host["name"]}')
                    fail.append(f'{host["name"]} ({host["hostname"]})')
            else:
                self.progress_signal.emit(f'{host["name"]} не в сети или не настроен ssh')
                logging.info(f'{host["hostname"]} не в сети или не настроен ssh')
                fail.append(f'{host["name"]} ({host["hostname"]})')
        if success_count == 0:
            self.progress_signal.emit(f"<br>{'Включение' if self.turn_autologin_on else 'Выключение'} "
                                      f"автологина не выполнено.")
        elif success_count < hosts_count:
            self.progress_signal.emit(
                f'<br>{"Включение" if self.turn_autologin_on else "Выключение"} автологина учеников завершено.<br>'
                f'<font color="red">Выполнено на {success_count} из {hosts_count} устройств.</font>')
            self.progress_signal.emit(f'<br>Не выполнено на устройствах: {", ".join(fail)}')
        else:
            self.progress_signal.emit(
                f'{"Включение" if self.turn_autologin_on else "Выключение"} автологина учеников завершено.<br>'
                f'Успешно на {success_count} из {hosts_count} компьютеров.')
        self.finish_signal.emit("Готово")

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

    thread = AutologinThread(host_list, turn_autologin_on=True, parent=parent)
    thread.start_signal.connect(lambda message: QMessageBox.information(parent, "Начало", message))
    thread.progress_signal.connect(lambda message: QMessageBox.information(parent, "Прогресс", message))
    thread.finish_signal.connect(lambda message: QMessageBox.information(parent, "Завершение", message))
    thread.start()

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

    thread = AutologinThread(host_list, turn_autologin_on=False, parent=parent)
    thread.start_signal.connect(lambda message: QMessageBox.information(parent, "Начало", message))
    thread.progress_signal.connect(lambda message: QMessageBox.information(parent, "Прогресс", message))
    thread.finish_signal.connect(lambda message: QMessageBox.information(parent, "Завершение", message))
    thread.start()
