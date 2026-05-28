import time
import cv2
from cv_bridge import CvBridge
from rclpy.node import Node # for msg control
from std_msgs.msg import Header
from geometry_msgs.msg import TwistStamped,Twist
from sensor_msgs.msg import Image,LaserScan,Imu,JointState

SPEED = 1.0

class MessageBroker(Node):
    def __init__(self):
        super().__init__('msg_broker')
        self._init_sub_img()
        self._init_pub_vel()

    def _init_pub_vel(self):
        """Инициализация издателя движения"""
        self.pub_vel = self.create_publisher(
                TwistStamped,
                '/cmd_vel',
                10
        )

    def _init_sub_img(self):
        """Инициализация подписчика камеры"""
        self.sub_img = self.create_subscription(
            Image,
            '/camera/image',
            self.camera_image_callback,
            10
        )
        self.bridge = CvBridge()

    def close_publishers(self):
        """Закрытие всех инициализированных издателей перед закрытием брокера сообщении"""
        self.destroy_publisher(self.pub_vel)

    def close_subscribers(self):
        """Закрытие всех инициализированных подписчиков перед закрытием брокера сообщении"""
        self.destroy_subscription(self.sub_img)

    def close(self):
        """Закрытие брокера сообщении"""
        self.close_publishers()     
        self.close_subscribers()    
        self.destroy_node()         

    def create_move_msg(self,direction):
        """
        Создаёт сообщение вида TwistStamped с заранне заданым направлением
        Аргументы:
            direction(str): направление, в котором движется робот
        Возвращает:
            msg(TwsitStamped): сообщение движения
        """
        msg = TwistStamped()
        # Так как сообщение TwistStamped состоит из Header и Twist сообщении
        # Cоздаём Header сообщение
        msg.header = Header()
        msg.header.frame_id = "base_link" # Example frame ID

        msg.twist = Twist()

        # Фиксированные направления движения робота
        directions = {
            'forward':  ((SPEED,0.0,0.0),(0.0,0.0,0.0)),
            'backward': ((-SPEED,0.0,0.0),(0.0,0.0,0.0)),
            'left':     ((0.0,0.0,0.0),(0.0,0.0,SPEED)),
            'right':    ((0.0,0.0,0.0),(0.0,0.0,-SPEED)),
        }
        # Создаём Twist сообщение
        try:
            vec_lin,vec_ang = directions[direction]
            msg.twist.linear.x = vec_lin[0]
            msg.twist.linear.y = vec_lin[1]
            msg.twist.linear.z = vec_lin[2]
            msg.twist.angular.x = vec_ang[0]
            msg.twist.angular.y = vec_ang[1]
            msg.twist.angular.z = vec_ang[2]
        except:
            msg.twist.linear.x = 0
            msg.twist.linear.y = 0
            msg.twist.linear.z = 0
            msg.twist.angular.x = 0
            msg.twist.angular.y = 0
            msg.twist.angular.z = 0
        return msg
    
    def publish_move_msg(self,direction):
        """
        Публикация сообщение движения с заданым направлением движенеия
        Аргументы:
            direction(str): направление в котором двигается робот
        """
        msg = self.create_move_msg(direction)
        self.move_msg = msg
        self.pub_vel.publish(msg)

    def camera_image_callback(self,msg):
        """
        Идентификация меток в камере
        Аргументы: 
            msg: сообщение из топика /camera/image
        """
        try:
            # Конвертируем из сообщения в чёрно-белое изображение для более точной идентификации меток
            image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='mono8')
        except Exception as e:
            self.get_logger().error(f"Error converting image: {e}")
            return

        # ПОМЕЧАНИЕ: В Ubuntu cv2 имеет версию 4.6.0 
        # Тот же код но для версии 4.11.0
        #   aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_1000)
        #   parameters = cv2.aruco.DetectorParameters()
        #   detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
        #   corners, ids, rejected = detector.detectMarkers(image)

        # Идентификация меток
        aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_1000)
        parameters = cv2.aruco.DetectorParameters_create()
        corners, ids, rejected = cv2.aruco.detectMarkers(image, aruco_dict, parameters=parameters)
        if ids != None:            
            self.get_logger().info(f'Идентифицированные метки: {ids[0]}')
        else:
            pass
