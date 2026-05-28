import time
import rclpy
import threading
from rclpy.executors import MultiThreadedExecutor

from robot_data_collector import ComponentDataCollector
from message_broker import MessageBroker

class Robot:
    def __init__(self,):
        rclpy.init(args=None)
        self._init_msg_broker()

    def _init_msg_broker(self):
        """Инициализация брокера сообщении и сборщика данных с компонентов"""
        self.msg_broker = MessageBroker()
        self.data_collector = ComponentDataCollector()
        # Запускаем в отдельном потоке, чтобы была возможность взаимодействовать с роботом
        executor = MultiThreadedExecutor(num_threads=4)
        executor.add_node(self.msg_broker)
        executor.add_node(self.data_collector)
        self.spin_thread = threading.Thread(target=executor.spin, daemon=True)
        self.spin_thread.start()
        while not rclpy.ok():
            time.sleep(0.1)

    def destroy(self):
        """Уничтожение робота"""
        self.msg_broker.close() 
        self.data_collector.close()
        rclpy.shutdown()
        self.spin_thread.join() # Для правильной очистки потока 

    def get_sensors_data(self):
        """ Получение данных с компонентов роботоа"""
        data = self.data_collector.get_data()
        return data
  
    def move_forward(self): 
        """Двигает робота вперёд"""
        self.msg_broker.publish_move_msg('forward')

    def move_backward(self): 
        """Двигает робота назад"""
        self.msg_broker.publish_move_msg('backward')

    def turn_right(self):    
        """Поворачивает робота направо"""
        self.msg_broker.publish_move_msg('right')

    def turn_left(self):     
        """Поворачивает робота налево"""
        self.msg_broker.publish_move_msg('left')