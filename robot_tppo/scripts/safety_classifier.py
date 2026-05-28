import rclpy
import math
import time
from rclpy.node import Node

# Константы для настройки триггеров безопасности
THRESHOLD_PERCENT = 5
MAX_PITCH_ROLL_DEG = 15.0     # Максимальный угол наклона до потери устойчивости
MAX_JOINT_EFFORT = 5.0       # Порог фиксации попытки движения
CRITICAL_SPEED_POST_IMPACT = 0.3 # Скорость (рад/с), выше которой столкновение наносит повреждение

class SafetyClassifier(Node):
    def __init__(self):
        super().__init__('safety_classifier')
        self.stuck_timers = {}
        
        self.last_x = None
        self.last_y = None
        self.position_stuck_start_time = None

    def classify_data(self, data):
        data_lidar = data['lidar']['ranges']
        data_imu = data['imu']
        data_joint_states = data['joint_states']
        data_odom = data['odometry']['position']
        
        damage_color, damage_situation = self.check_joints_health(data_joint_states)                  # Определяем состояние приводов                
        collision_color, collision_situation = self.check_safety_zones(data_lidar, data_joint_states) # Проверяем коллизии и повреждения конструкции
        
        # Если коллизия выявила структурное повреждение от удара, переопределяем статус Damage
        if collision_situation == 'ROBOT_DAMAGE':
            damage_color = 'red'
            damage_situation = 'ROBOT_DAMAGE'
        
        stability_color, stability_situation = self.check_stability(data_imu)                         # Проверяем устойчивость платформы               
        uncontrolled_color, uncontrolled_situation = self.check_global_movement(data_odom, data_joint_states) # Проверяем застревание по неизменяемости координат

        if uncontrolled_situation == 'UNCONTROLLED_STUCK':
            damage_color = 'red'
            damage_situation = 'UNCONTROLLED_STUCK'            
        elif uncontrolled_situation == 'MOVEMENT_BLOCKED':
            damage_color = 'yellow'
            damage_situation = 'MOVEMENT_BLOCKED'                
        else:
            pass

        results = {
            "Collision": {
                "status": collision_color,
                "situation": collision_situation
            },
            "Stability": {
                "status": stability_color,
                "situation": stability_situation
            },
            "Damage": {
                "status": damage_color,
                "situation": damage_situation
            }
        }
        return results 

    def check_safety_zones(self, ranges, joint_data=None):
        """Классификация: Препятствие, Столкновение с объектом и Повреждение робота"""
        counts = {'green': 0, 'yellow': 0, 'red': 0}
        has_impact_contact = False 
        
        valid_distances = []
        for distance in ranges.values():
            if distance is None or distance == 'None':
                continue
            try:
                dist = float(distance)
                if 0.0 < dist < 50.0: 
                    valid_distances.append(dist)
            except ValueError:
                continue

        if not valid_distances:
            return 'green', 'OK'

        min_dist = min(valid_distances)

        if min_dist < 0.28:
            has_impact_contact = True

        for dist in valid_distances:
            if dist > 1.0:
                counts['green'] += 1
            elif dist > 0.4:
                counts['yellow'] += 1
            else:
                counts['red'] += 1

        if has_impact_contact:
            max_current_speed = 0.0
            if joint_data:
                for j_name, j_info in joint_data.items():
                    vel = j_info.get('velocity')
                    if vel is not None and vel != 'None':
                        max_current_speed = max(max_current_speed, abs(float(vel)))

            if max_current_speed > CRITICAL_SPEED_POST_IMPACT:
                return 'red', 'ROBOT_DAMAGE'
            
            return 'red', 'COLLISION_IMPACT'

        percent = lambda color: color / len(valid_distances) * 100
        if percent(counts['red']) > THRESHOLD_PERCENT or (percent(counts['yellow']) > THRESHOLD_PERCENT and percent(counts['red']) > 0):
            return 'red', 'ENVIRONMENT_DAMAGE'
        elif percent(counts['yellow']) > THRESHOLD_PERCENT: 
            return 'yellow', 'OBSTACLE_AHEAD'
        else:
            return 'green', 'OK'

    def check_stability(self, imu_data):
        """Классификация: Устойчивость платформы"""
        if not imu_data:
            return 'green', 'OK'
            
        orientation = imu_data.get('orientation', {})
        x, y, z, w = orientation.get('x'), orientation.get('y'), orientation.get('z'), orientation.get('w')

        if any(v is None or v == 'None' for v in [x, y, z, w]):
            return 'green', 'OK'

        try:
            sinr_cosp = 2 * (w * x + y * z)
            cosr_cosp = 1 - 2 * (x * x + y * y)
            roll = math.atan2(sinr_cosp, cosr_cosp)

            sinp = 2 * (w * y - z * x)
            pitch = math.copysign(math.pi / 2, sinp) if abs(sinp) >= 1 else math.asin(sinp)

            roll_deg = abs(math.degrees(roll))
            pitch_deg = abs(math.degrees(pitch))

            if roll_deg > MAX_PITCH_ROLL_DEG or pitch_deg > MAX_PITCH_ROLL_DEG:
                return 'red', 'LOSS_OF_STABILITY'
            elif roll_deg > (MAX_PITCH_ROLL_DEG * 0.7) or pitch_deg > (MAX_PITCH_ROLL_DEG * 0.7):
                return 'yellow', 'STABILITY_WARNING'

        except Exception:
            pass
            
        return 'green', 'OK'

    def check_joints_health(self, joint_data):
        """Проверка нагрузка на суставы"""
        if not joint_data:
            return 'green', 'OK'
            
        any_high_load = False

        for joint_name, data in joint_data.items():
            effort_val = data.get('effort')
            if effort_val is None or effort_val == 'None':
                continue
                
            try:
                effort = abs(float(effort_val))
                if effort > MAX_JOINT_EFFORT:
                    any_high_load = True
            except ValueError:
                continue
        
        if any_high_load:
            return 'yellow', 'JOINT_OVERLOAD'
            
        return 'green', 'OK'

    def check_global_movement(self, odom_position, joint_data):
        """
        Проверяет, не застрял ли робот
        """
        current_time = time.time()
        
        try:
            current_x = float(odom_position.get('x', 0.0))
            current_y = float(odom_position.get('y', 0.0))
        except (ValueError, TypeError):
            return 'green', 'OK'

        # Сбор текущих позиций колес
        current_joints_positions = {}
        if joint_data:
            for j_name, data in joint_data.items():
                try:
                    pos_val = data.get('position')
                    if pos_val is not None:
                        current_joints_positions[j_name] = float(pos_val)
                except (ValueError, TypeError):
                    continue

        # Первая инициализация
        if self.last_x is None or self.last_y is None:
            self.last_x = current_x
            self.last_y = current_y
            self.last_joints_positions = current_joints_positions
            self.position_stuck_start_time = current_time
            return 'green', 'OK'

        # Проверяем изменение координат относительно ОПОРНОЙ точки (last_x/y)
        robot_moved = (abs(current_x - self.last_x) > 0.005) or (abs(current_y - self.last_y) > 0.005)

        # Проверяем, крутятся ли колеса
        wheels_turned = False
        for j_name, current_pos in current_joints_positions.items():
            past_pos = self.last_joints_positions.get(j_name)
            if past_pos is not None:
                if abs(current_pos - past_pos) > 0.01:
                    wheels_turned = True
                    break

        if robot_moved:           
            self.last_x = current_x
            self.last_y = current_y
            self.last_joints_positions = current_joints_positions
            self.position_stuck_start_time = current_time
            return 'green', 'OK'

        if wheels_turned:
            elapsed_time = current_time - self.position_stuck_start_time            
            if elapsed_time >= 5.0:
                return 'red', 'UNCONTROLLED_STUCK'
            elif elapsed_time >= 1.5:
                return 'yellow', 'MOVEMENT_BLOCKED'
        else:
            self.last_joints_positions = current_joints_positions
            self.position_stuck_start_time = current_time

        return 'green', 'OK'