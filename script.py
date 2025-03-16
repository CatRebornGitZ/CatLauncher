import sys
import json
import random
from PyQt5.QtCore import QThread, pyqtSignal, QSize, Qt, QPropertyAnimation, QRect, QTimer, QSettings
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QComboBox, QSpacerItem, QSizePolicy, QProgressBar, QPushButton,
    QApplication, QMainWindow, QTextEdit, QMessageBox, QDialog, QFormLayout
)
from PyQt5.QtGui import QPixmap, QFont, QColor, QPalette

from minecraft_launcher_lib.utils import get_minecraft_directory, get_version_list
from minecraft_launcher_lib.install import install_minecraft_version
from minecraft_launcher_lib.command import get_minecraft_command

from random_username.generate import generate_username
from uuid import uuid1

from subprocess import call

minecraft_directory = get_minecraft_directory().replace('minecraft', 'mjnlauncher')

# Файл для сохранения настроек
SETTINGS_FILE = "launcher_settings.json"


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setGeometry(200, 200, 300, 200)

        # Настройки
        self.settings = QSettings("MinecraftLauncher", "Settings")

        # Создаем layout
        layout = QVBoxLayout()

        # Выбор языка
        language_label = QLabel("Язык:")
        self.language_combo = QComboBox()
        self.language_combo.addItem("Русский", "ru")
        self.language_combo.addItem("Английский", "en")
        current_lang = self.settings.value("language", "ru")
        index = self.language_combo.findData(current_lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        layout.addWidget(language_label)
        layout.addWidget(self.language_combo)

        # Выбор темы
        theme_label = QLabel("Тема:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Светлая", "light")
        self.theme_combo.addItem("Темная", "dark")
        current_theme = self.settings.value("theme", "light")
        index = self.theme_combo.findData(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        layout.addWidget(theme_label)
        layout.addWidget(self.theme_combo)

        # Выбор анимации
        animation_label = QLabel("Анимация:")
        self.animation_combo = QComboBox()
        self.animation_combo.addItem("Снег", "snow")
        self.animation_combo.addItem("Кубики", "cubes")
        self.animation_combo.addItem("Выключено", "off")
        current_animation = self.settings.value("animation", "cubes")
        index = self.animation_combo.findData(current_animation)
        if index >= 0:
            self.animation_combo.setCurrentIndex(index)
        layout.addWidget(animation_label)
        layout.addWidget(self.animation_combo)

        # Аргументы Java
        java_args_label = QLabel("Аргументы Java:")
        self.java_args_input = QLineEdit(self.settings.value("java_args", "-Xmx2G -Xms1G"))
        layout.addWidget(java_args_label)
        layout.addWidget(self.java_args_input)

        # Кнопки "Сохранить" и "Отмена"
        buttons_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.close)
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def save_settings(self):
        # Сохраняем настройки
        self.settings.setValue("language", self.language_combo.currentData())
        self.settings.setValue("theme", self.theme_combo.currentData())
        self.settings.setValue("animation", self.animation_combo.currentData())
        self.settings.setValue("java_args", self.java_args_input.text())
        QMessageBox.information(self, "Сохранено", "Настройки успешно сохранены!")
        self.close()


class LaunchThread(QThread):
    launch_setup_signal = pyqtSignal(str, str, str)
    progress_update_signal = pyqtSignal(int, int, str)
    state_update_signal = pyqtSignal(bool)

    version_id = ''
    username = ''
    java_args = ''

    progress = 0
    progress_max = 0
    progress_label = ''

    def __init__(self):
        super().__init__()
        self.launch_setup_signal.connect(self.launch_setup)

    def launch_setup(self, version_id, username, java_args):
        self.version_id = version_id
        self.username = username
        self.java_args = java_args

    def update_progress_label(self, value):
        self.progress_label = value
        self.progress_update_signal.emit(self.progress, self.progress_max, self.progress_label)

    def update_progress(self, value):
        self.progress = value
        self.progress_update_signal.emit(self.progress, self.progress_max, self.progress_label)

    def update_progress_max(self, value):
        self.progress_max = value
        self.progress_update_signal.emit(self.progress, self.progress_max, self.progress_label)

    def run(self):
        self.state_update_signal.emit(True)

        install_minecraft_version(versionid=self.version_id, minecraft_directory=minecraft_directory,
                                 callback={'setStatus': self.update_progress_label, 'setProgress': self.update_progress,
                                          'setMax': self.update_progress_max})

        if self.username == '':
            self.username = generate_username()[0]

        options = {
            'username': self.username,
            'uuid': str(uuid1()),
            'token': '',
            'jvmArguments': self.java_args.split()
        }

        call(get_minecraft_command(version=self.version_id, minecraft_directory=minecraft_directory, options=options))
        self.state_update_signal.emit(False)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(800, 500)
        self.centralwidget = QWidget(self)

        # Основной горизонтальный layout
        self.horizontal_layout = QHBoxLayout(self.centralwidget)
        self.horizontal_layout.setContentsMargins(15, 15, 15, 15)

        # Левая панель (меню)
        self.left_panel = QWidget(self.centralwidget)
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(0, 0, 0, 0)

        # Устанавливаем черную тему по умолчанию
        self.set_dark_theme()

        # Заголовок CatLauncher
        self.title_label = QLabel("CatLauncher", self.left_panel)
        self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.title_label.setStyleSheet("color: black;" if self.is_light_theme() else "color: white;")
        self.left_layout.addWidget(self.title_label, alignment=Qt.AlignCenter)

        # Поле для ввода имени пользователя
        self.username = QLineEdit(self.left_panel)
        self.username.setPlaceholderText("Имя пользователя")
        self.username.setStyleSheet("color: black; background-color: white;" if self.is_light_theme() else "color: white; background-color: #353535;")
        self.left_layout.addWidget(self.username)

        # Выбор версии Minecraft
        self.version_select = QComboBox(self.left_panel)
        try:
            for version in get_version_list():
                self.version_select.addItem(version['id'])
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить список версий: {e}")
            self.version_select.addItem("1.8.9")  # Версия по умолчанию
        self.version_select.setStyleSheet("color: black; background-color: white;" if self.is_light_theme() else "color: white; background-color: #353535;")
        self.left_layout.addWidget(self.version_select)

        # Кнопка "Играть"
        self.start_button = QPushButton("Играть", self.left_panel)
        self.start_button.clicked.connect(self.launch_game)
        self.start_button.setStyleSheet("color: black; background-color: #D3D3D3;" if self.is_light_theme() else "color: white; background-color: #4C566A;")
        self.left_layout.addWidget(self.start_button)

        # Кнопка "Настройки"
        self.settings_button = QPushButton("Настройки", self.left_panel)
        self.settings_button.clicked.connect(self.open_settings)
        self.settings_button.setStyleSheet("color: black; background-color: #D3D3D3;" if self.is_light_theme() else "color: white; background-color: #4C566A;")
        self.left_layout.addWidget(self.settings_button)

        # Добавляем левую панель в основной layout
        self.horizontal_layout.addWidget(self.left_panel)

        # Правая панель (логи)
        self.right_panel = QWidget(self.centralwidget)
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)

        # Текстовое поле для логов
        self.log_text = QTextEdit(self.right_panel)
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("color: black; background-color: white;" if self.is_light_theme() else "color: white; background-color: #353535;")
        self.right_layout.addWidget(self.log_text)

        # Прогресс бар и его описание
        self.start_progress_label = QLabel(self.right_panel)
        self.start_progress_label.setText('')
        self.start_progress_label.setStyleSheet("color: black;" if self.is_light_theme() else "color: white;")
        self.start_progress_label.setVisible(False)

        self.start_progress = QProgressBar(self.right_panel)
        self.start_progress.setProperty('value', 0)
        self.start_progress.setStyleSheet("color: black; background-color: white;" if self.is_light_theme() else "color: white; background-color: #353535;")
        self.start_progress.setVisible(False)
        self.right_layout.addWidget(self.start_progress_label)
        self.right_layout.addWidget(self.start_progress)

        # Добавляем правую панель в основной layout
        self.horizontal_layout.addWidget(self.right_panel)

        # Поток для запуска игры
        self.launch_thread = LaunchThread()
        self.launch_thread.state_update_signal.connect(self.state_update)
        self.launch_thread.progress_update_signal.connect(self.update_progress)

        # Загружаем сохраненные настройки
        self.load_settings()

        # Список анимаций
        self.animations = []
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(1000)  # Обновление анимации каждую секунду

        self.setCentralWidget(self.centralwidget)

    def is_light_theme(self):
        # Проверяем, активна ли светлая тема
        return QApplication.palette().color(QPalette.Window).lightness() > 127

    def update_animation(self):
        # Обновляем анимацию в зависимости от выбранного типа
        animation_type = QSettings("MinecraftLauncher", "Settings").value("animation", "cubes")
        if animation_type == "snow":
            self.create_snowflake()
        elif animation_type == "cubes":
            self.create_cube()
        elif animation_type == "off":
            pass  # Анимация выключена

    def create_snowflake(self):
        # Создаем снежинку
        snowflake = QLabel(self)
        snowflake.setPixmap(QPixmap("snowflake.png").scaled(20, 20))  # Загрузите изображение снежинки
        snowflake.move(random.randint(0, 800), 0)
        snowflake.show()

        # Анимация падения снежинки
        animation = QPropertyAnimation(snowflake, b"geometry")
        animation.setDuration(random.randint(3000, 5000))  # Случайная длительность
        animation.setStartValue(QRect(snowflake.x(), snowflake.y(), 20, 20))
        animation.setEndValue(QRect(snowflake.x(), 500, 20, 20))  # Падение вниз
        animation.start()

        # Добавляем снежинку и анимацию в списки
        self.animations.append((snowflake, animation))

        # Удаляем снежинку и анимацию после завершения
        animation.finished.connect(lambda: self.remove_animation(snowflake, animation))

    def create_cube(self):
        # Создаем кубик
        cube = QLabel(self)
        cube.setStyleSheet("background-color: red; border: 2px solid black;")
        cube.setFixedSize(50, 50)
        cube.move(800, random.randint(0, 450))  # Появляется справа на случайной высоте
        cube.show()

        # Анимация перемещения кубика влево
        animation = QPropertyAnimation(cube, b"geometry")
        animation.setDuration(3000)  # Длительность анимации
        animation.setStartValue(QRect(800, cube.y(), 50, 50))
        animation.setEndValue(QRect(-100, cube.y(), 50, 50))  # Уходит за пределы окна
        animation.start()

        # Добавляем кубик и анимацию в списки
        self.animations.append((cube, animation))

        # Удаляем кубик и анимацию после завершения
        animation.finished.connect(lambda: self.remove_animation(cube, animation))

    def remove_animation(self, widget, animation):
        # Удаляем виджет и анимацию из списков
        widget.deleteLater()
        animation.deleteLater()
        self.animations = [(w, a) for (w, a) in self.animations if w != widget]

    def load_settings(self):
        # Загружаем сохраненные настройки
        try:
            with open(SETTINGS_FILE, "r") as file:
                settings = json.load(file)
                self.username.setText(settings.get("username", ""))
                self.version_select.setCurrentText(settings.get("version", "1.8.9"))
        except FileNotFoundError:
            pass

    def save_settings(self):
        # Сохраняем текущие настройки
        settings = {
            "username": self.username.text(),
            "version": self.version_select.currentText()
        }
        with open(SETTINGS_FILE, "w") as file:
            json.dump(settings, file)

    def set_dark_theme(self):
        # Устанавливаем черную тему
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        QApplication.setPalette(dark_palette)

    def set_light_theme(self):
        # Устанавливаем светлую тему
        light_palette = QPalette()
        light_palette.setColor(QPalette.Window, Qt.white)
        light_palette.setColor(QPalette.WindowText, Qt.black)
        light_palette.setColor(QPalette.Base, QColor(240, 240, 240))
        light_palette.setColor(QPalette.AlternateBase, Qt.white)
        light_palette.setColor(QPalette.ToolTipBase, Qt.white)
        light_palette.setColor(QPalette.ToolTipText, Qt.black)
        light_palette.setColor(QPalette.Text, Qt.black)
        light_palette.setColor(QPalette.Button, QColor(240, 240, 240))
        light_palette.setColor(QPalette.ButtonText, Qt.black)
        light_palette.setColor(QPalette.BrightText, Qt.red)
        light_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        light_palette.setColor(QPalette.HighlightedText, Qt.white)
        QApplication.setPalette(light_palette)

    def open_settings(self):
        # Открываем окно настроек
        dialog = SettingsDialog(self)
        dialog.exec_()
        self.apply_settings()

    def apply_settings(self):
        # Применяем настройки
        settings = QSettings("MinecraftLauncher", "Settings")
        theme = settings.value("theme", "light")
        if theme == "dark":
            self.set_dark_theme()
        else:
            self.set_light_theme()

    def state_update(self, value):
        self.start_button.setDisabled(value)
        self.settings_button.setDisabled(value)
        self.start_progress_label.setVisible(value)
        self.start_progress.setVisible(value)

    def update_progress(self, progress, max_progress, label):
        self.start_progress.setValue(progress)
        self.start_progress.setMaximum(max_progress)
        self.start_progress_label.setText(label)

    def launch_game(self):
        version = self.version_select.currentText()
        username = self.username.text()
        java_args = QSettings("MinecraftLauncher", "Settings").value("java_args", "-Xmx2G -Xms1G")
        self.log_text.append(f"Выполнение команды: {version}")
        self.launch_thread.launch_setup_signal.emit(version, username, java_args)
        self.launch_thread.start()
        self.save_settings()  # Сохраняем настройки перед запуском


if __name__ == '__main__':
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())