import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from launch.actions import IncludeLaunchDescription,ExecuteProcess,RegisterEventHandler, Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.event_handlers import OnProcessExit

import tkinter as tk
import tkinter as ttk
from tkinter.filedialog import askopenfilename
from tkinter.messagebox import showerror, showinfo

pkg_share = get_package_share_directory('robot_tppo')
# Пространства на которых производилось тестирование:
# - aruco.sdf,
# - colorful_scene.sdf
# - default.sdf
DEFAULT_WORLD_FILE = os.path.join(pkg_share,'worlds','default.sdf')
DEFAULT_WORLD_FILE = os.path.join(pkg_share,'worlds','test_new.sdf')
world_file = DEFAULT_WORLD_FILE

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry('500x500')
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self._init_widgets()
        self._pack_all()
        self.mainloop()

    def _init_widgets(self):
        self.world_title              = tk.Label( self, text="Пространство (sdf)") 
        self.world_file_entry         = tk.Entry( self, state='readonly')
        self.world_file_pick_button   = tk.Button(self, text='Загрузить пространство', command = self.update_world_file_entry)

        self.start_simulation_button = tk.Button(self, text='Запуск', command=self.start_simulation)

    def _pack_all(self):
        self.world_title.grid(row=1,column=1)
        self.world_file_entry.grid(row=2,column=1)
        self.world_file_pick_button.grid(row=2,column=2)
        self.start_simulation_button.grid(row=5,column=1)

    def close_app(self):
        """ Закрытие программы"""
        self.quit()
        self.destroy()
        exit()          # Иначе программа продолжит работать после закрытия окна приложения 

    def start_simulation(self):
        """Запуск симуляции"""
        self.quit()     
        self.destroy()

    def update_world_file_entry(self):
        """Ввод файла пространства"""
        filepath = askopenfilename(
            initialdir=os.path.join(pkg_share, 'worlds'),
            title='Выберите файл пространства',
            filetypes = [
               ("Файл пространства", "*.sdf")
            ]
        )

        if filepath == '' or filepath == (): # Если пользователь закроет окно выбора файла, не выбрав файл 
            return
        global world_file
        world_file = filepath

        self.world_file_entry.config(state='normal')
        self.world_file_entry.delete(0, tk.END)
        self.world_file_entry.insert(0, filepath)
        self.world_file_entry.config(state='readonly')

def generate_launch_description():
    App()
    xacro_file = os.path.join(pkg_share, 'urdf', 'robot.urdf.xacro')
    rviz_config_file = os.path.join(pkg_share, 'rviz', 'urdf.rviz')
    controller_params_file = os.path.join(pkg_share, 'config', 'diff_drive_controllers.yaml')

    robot_description_substitution = Command(['xacro ', xacro_file])
    robot_description = ParameterValue(robot_description_substitution, value_type=str)
    robot_description_param = {'robot_description': robot_description}

    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[robot_description_param]  
    )

    joint_state_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster',"--controller-manager-timeout", "120", "--switch-timeout", "100"], 
        output='screen',  
    )

    diff_drive_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'diff_drive_controller',  
            '--param-file', 
            controller_params_file,
            '--controller-ros-args',
            '-r /diff_drive_controller/cmd_vel:=/cmd_vel',
            "--controller-manager-timeout", "120", "--switch-timeout", "100",
        ],
        output='screen',
        parameters=[{'use_sim_time': True}]
    )

    # RViz 
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_file],
        output='screen'
    )

    # Запуск GZ Sim 
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ]),
        launch_arguments={
            'gz_args': f'-r {world_file}',
            'use_sim_time': 'true',
            'on_exit_shutdown': 'true'
            }.items()
    )

    # Спавн робота в GZ Sim 
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'robot_tppo',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.6'
        ],
        output='screen'
    )

    ## Bridge для преобразования сообщений между ROS и GZ
    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/TwistStamped@gz.msgs.TwistStamped',
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',  
            "/camera/image@sensor_msgs/msg/Image@gz.msgs.Image",
            "/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
            "/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan",
            "/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry",
            "/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V",
            "imu@sensor_msgs/msg/Imu@gz.msgs.IMU",
            '/model/robot_tppo/odometry_with_covariance@nav_msgs/msg/Odometry@gz.msgs.OdometryWithCovariance',           
        ],
        output='screen',
    ) 
    
    executables_list = [        
        rsp_node,
        #rviz_node,
        gz_sim,
        gz_bridge,
        spawn_entity,
        joint_state_spawner,
        diff_drive_spawner,
    ]

    launch_gui = ExecuteProcess(
            cmd=['python3', 
                 os.path.join(pkg_share, 'scripts','app.py'),
            ]
    )
    shutdown_on_app_exit = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=launch_gui,
            on_exit=[
               Shutdown()
            ]
        )
    )

    executables_list.extend([launch_gui,shutdown_on_app_exit])

    return LaunchDescription(executables_list)
