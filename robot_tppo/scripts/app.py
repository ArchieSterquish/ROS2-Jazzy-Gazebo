from gui.control_frame import RobotControlFrame
from gui.nested_table import NestedTable
from gui.event_classifier_frame import EventClassifierFrame
from robot import Robot

import subprocess
import os
import tkinter as tk
from tkinter.filedialog import askopenfilename
from ament_index_python.packages import get_package_share_directory
from rclpy.logging import get_logger

from safety_classifier import SafetyClassifier

class AppComponentData(tk.Tk):
    def __init__(self):
        super().__init__()
        self._init_robot()
        self._init_widgets()
        self.geometry('750x600')
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.update() # запускаем получение данных с робота 
        self.mainloop()

    def _init_robot(self):
        """Инициализация робота"""
        self.robot = Robot()
        self.safety_classifier = SafetyClassifier()
        #self.safety_classifier = SafeClass()

    def _init_widgets(self):
        """Инициализация виджетов и их взаимное расположение"""
        # Создаем контейнер верхнего уровня для двух таблиц, чтобы они стояли в один ряд
        self.top_tables_frame = tk.Frame(self)
        self.top_tables_frame.pack(side=tk.TOP, fill='both', expand=True, padx=10, pady=5)

        # 1. Инициализируем классификатор и крепим его СЛЕВА
        self.event_classifier_frame = EventClassifierFrame(self.top_tables_frame)
        self.event_classifier_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=(0, 5))

        # 2. Инициализируем дерево данных робота NestedTable и крепим его СПРАВА
        self.table = NestedTable(self.top_tables_frame)
        data = self.get_robot_data()
        self.table.build_tree(data)
        self.table.pack(side=tk.LEFT, fill='both', expand=True, padx=(5, 0))

        # 3. Нижний фрейм управления (Остается без изменений)
        self.big_frame = tk.Frame(self)
        self.control_frame = RobotControlFrame(self.big_frame, self.robot)
        
        # Виджеты отправки скриптов/команд
        frame = tk.Frame(self.big_frame)
        tk.Label(frame, text="Команды (py)").grid(row=1, column=1)
        self.commands_file_entry = tk.Entry(frame, state='readonly')
        self.commands_file_entry.grid(row=2, column=1)
        tk.Button(frame, text='Загрузить файл команд', command=self.update_commands_file_entry).grid(row=2, column=2)
        tk.Button(frame, text='Запустить команды', command=self.execute_commands).grid(row=3, column=1)
        
        frame.grid(row=0, column=1, padx=30)
        self.control_frame.grid(row=0, column=0)
        
        # Упаковываем нижний пульт управления под таблицами
        self.big_frame.pack(side=tk.TOP, pady=10)
        self.commands_file = None

    def update_commands_file_entry(self):
        """Ввод файла команд"""
        pkg_share = get_package_share_directory('robot_tppo')
        filepath = askopenfilename(
            initialdir=os.path.join(pkg_share, 'scripts'),
            title='Выберите файл команд',
            filetypes = [
               ("Файл команд", "*.py")
            ]
        )

        if filepath == '' or filepath == (): # Чтобы избежать случая когда пользователь закрыл окно выбора файл не выбрав файл 
            return
        self.commands_file = filepath

        self.commands_file_entry.config(state='normal')
        self.commands_file_entry.delete(0, tk.END)
        self.commands_file_entry.insert(0, filepath)
        self.commands_file_entry.config(state='readonly')

    def execute_commands(self):
        """Исполнение файла команд"""
        if self.commands_file != None or self.commands_file != '':
            subprocess.Popen(
                ["python3", self.commands_file],
                capture_output=True,
                text=True
            )           
        
    def get_robot_data(self):
        """Получение данных компонент робота"""
        data = self.robot.get_sensors_data()        
        return data

    def close_app(self):
        """Закрытие приложения"""
        self.robot.destroy()
        self.quit()
        self.destroy()
        exit()

    def update(self):
        """Обновление данных компонент робота"""
        data = self.get_robot_data()
        self.table.update_values(data)  

        event_safety_classification = self.safety_classifier.classify_data(data)
        
        self.event_classifier_frame.update_status(
            event_safety_classification, 
            safety_classifier_node=self.safety_classifier
        )

        self.after(1, self.update)

AppComponentData()