import tkinter as tk
from tkinter import ttk
import datetime

class EventClassifierFrame(tk.LabelFrame):
    def __init__(self, root):
        super().__init__(root, text="История опасных событий")
        
        self.tree = ttk.Treeview(self, columns=("time", "danger", "description"), show="headings", height=8)
        
        self.tree.heading("time", text="Время")
        self.tree.heading("danger", text="Опасность")
        self.tree.heading("description", text="Описание ситуации")
        
        self.tree.column("time", width=80, anchor="center", stretch=False)
        self.tree.column("danger", width=100, anchor="center", stretch=False)
        self.tree.column("description", width=450, anchor="w")
        
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, expand=True, fill="both", padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        self.tree.tag_configure("GREEN", foreground="green", font=("Arial", 9))
        self.tree.tag_configure("YELLOW", foreground="orange", font=("Arial", 9, "bold"))
        self.tree.tag_configure("RED", foreground="red", font=("Arial", 9, "bold"))
        
        # Храним состояние для каждой системы
        self.last_states = {
            "Collision": ("GREEN", "OK"),
            "Stability": ("GREEN", "OK"),
            "Damage":    ("GREEN", "OK")
        }


    def update_status(self, status_dict, safety_classifier_node=None):
        """
        Обновление статуса опасности
        """
        if not isinstance(status_dict, dict):
            return

        time_str = datetime.datetime.now().strftime("%H:%M:%S")

        for system, info in status_dict.items():
            # Защита от ошибки: проверяем, является ли info словарем или строкой
            if isinstance(info, dict):
                status_upper = str(info.get("status", "GREEN")).upper()
                event_type = info.get("situation", "OK")
            else:
                status_upper = str(info).upper()
                event_type = "OK" if status_upper == "GREEN" else f"{system.upper()}_WARN"
            
            sys_name = "Коллизии" if system == "Collision" else "Устойчивость" if system == "Stability" else "Приводы"

            DESCRIPTION_EVENT = {
                "COLLISION_IMPACT":  "Внимание: Зафиксировано прямое столкновение с объектом!",
                "ROBOT_DAMAGE":      "Критическая авария: Робот поврежден из-за удара на скорости!",
                "UNCONTROLLED_STUCK":"Авария: Робот неконтролируем (приводы заблокированы более 5 секунд).",
                "LOSS_OF_STABILITY": "Опасность: Робот потерял устойчивость платформы.",
                "ENVIRONMENT_DAMAGE":"Предупреждение: Высокий риск повреждения среды.",
                "MOVEMENT_BLOCKED":  "Предупреждение: Штатное движение робота затруднено.",
                "STABILITY_WARNING": "Предупреждение: Опасный угол наклона платформы.",
                "OBSTACLE_AHEAD":    "Предупреждение: Обнаружено препятствие на пути.",
            }

            # Словарь человекочитаемых описаний новых ситуаций
            if status_upper == "GREEN":
                description = f"Система [{sys_name}] работает штатно."
                event_type = "OK"
            else:
                if event_type in DESCRIPTION_EVENT.keys():
                    description = DESCRIPTION_EVENT[event_type]
                else:
                    description = f"Событие в секции [{sys_name}]: {event_type}"

            last_color, last_type = self.last_states.get(system, ("GREEN", "OK"))

            if status_upper != last_color or (status_upper != "GREEN" and event_type != last_type):
                self.last_states[system] = (status_upper, event_type)
                self.tree.insert("", 0, values=(time_str, status_upper, description), tags=(status_upper,))