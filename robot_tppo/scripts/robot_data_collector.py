from rclpy.node import Node 
from sensor_msgs.msg import Image,LaserScan,Imu,JointState
from nav_msgs.msg import Odometry

class ComponentDataCollector(Node):
    def __init__(self):
        super().__init__('component_data_collector')
        self._init_subscribers()
        self.data_lidar = {
            "ranges":{f"{i}":100 for i in range(30)} # 100 до инициализации
        }
        self.data_imu = {
            "orientation":          {"x":'None',"y":'None',"z":'None',"w":'None',},
            "angular_velocity":     {"x":'None',"y":'None',"z":'None',},
            "linear_acceleration":  {"x":'None',"y":'None',"z":'None',}
        }
        joints = [
                "left_front_wheel_joint",
                "left_rear_wheel_joint",
                "right_front_wheel_joint",
                "right_rear_wheel_joint"
        ]
        self.data_joint_states = {j:{'position':'None','velocity':'None','effort':'None'} for j in joints}
        self.data_odom = {"position": {"x":'None',"y":'None'}}

    def _init_subscribers(self):
        """Инициализация подписчиков"""
        self.sub_joint_states = self.create_subscription(JointState,'/joint_states',self.joint_states_callback,10)
        self.sub_imu          = self.create_subscription(Imu,'/imu',self.imu_callback,10)
        self.sub_lidar        = self.create_subscription(LaserScan,'/scan',self.lidar_callback,10)        
        self.sub_odom         = self.create_subscription(Odometry, '/model/robot_tppo/odometry_with_covariance', self.odom_callback, 10)

    def close_subscribers(self):
        """Закрытие всех инициализированных подписчиков перед закрытием брокера сообщении"""
        self.destroy_subscription(self.sub_joint_states) 
        self.destroy_subscription(self.sub_imu)          
        self.destroy_subscription(self.sub_lidar)        

    def close(self):
        """Закрытие брокера сообщении"""
        self.close_subscribers()    
        self.destroy_node()         

    def get_data(self):
        """Получение текущих данных компонентов"""
        return {
            'joint_states': self.data_joint_states,
            'imu': self.data_imu,
            'lidar': self.data_lidar,
            'odometry': self.data_odom,
        }

    def lidar_callback(self,msg):
        """Callback при получении сообщения с лидара"""
        for i,data in enumerate(msg.ranges):
            self.data_lidar['ranges'][f"{i}"] = data

    def imu_callback(self,msg):
        """Callback при получении сообщения с инерциального датчика"""
        o = msg.orientation
        a = msg.angular_velocity
        l = msg.linear_acceleration

        self.data_imu["orientation"]["x"] = o.x
        self.data_imu["orientation"]["y"] = o.y
        self.data_imu["orientation"]["z"] = o.z
        self.data_imu["orientation"]["w"] = o.w

        self.data_imu["angular_velocity"]["x"] = a.x
        self.data_imu["angular_velocity"]["y"] = a.y
        self.data_imu["angular_velocity"]["z"] = a.z

        self.data_imu["linear_acceleration"]["x"] = a.x
        self.data_imu["linear_acceleration"]["y"] = a.y
        self.data_imu["linear_acceleration"]["z"] = a.z

    def joint_states_callback(self,msg):
        """Callback при получении сообщения с соединении с колёсами"""
        for i in range(len(msg.name)):
            self.data_joint_states[msg.name[i]] = {
                    "position": msg.position[i],
                    "velocity": msg.velocity[i],
                    "effort"  : msg.effort[i]
            }
    
    def odom_callback(self, msg):
        """Callback для разбора координат x, y, z из сообщения Odometry"""
        pos = msg.pose.pose.position
        self.data_odom["position"]["x"] = pos.x
        self.data_odom["position"]["y"] = pos.y
