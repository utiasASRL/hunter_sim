import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PythonExpression, TextSubstitution, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import launch_ros.descriptions

import launch
import launch.launch_description_sources
import launch.substitutions
import launch_ros
import launch_ros.substitutions
 
def generate_launch_description():
 
  # Constants for paths to different files and folders
  gazebo_models_path = 'models'
  package_name = 'hunter2_base'
  robot_name_in_model = 'hunter2'
  rviz_config_file_path = 'rviz/urdf.rviz'
  urdf_file_path = 'urdf/hunter2_base_gazebo_lidar.xacro'
  urdf_file_path_2 = 'urdf/hunter2_base_gazebo_lidar_2.xacro'
  urdf_file_path_3 = 'urdf/hunter2_base_gazebo_lidar_3.xacro'
  world_file_path = 'world/mars_dome.world'
 
  # Pose where we want to spawn the robot
  spawn_x_val = '3'
  spawn_y_val = '0.0'
  spawn_z_val = '-0.6'
  spawn_yaw_val = '0.00'

  spawn_x_val_2 = str(float(spawn_x_val) - 4)
  spawn_x_val_3 = str(float(spawn_x_val) - 2)

  ############ You do not need to change anything below this line #############
 
  # Set the path to different files and folders.     
  pkg_share = FindPackageShare(package=package_name).find(package_name)
  default_urdf_model_path = os.path.join(pkg_share, urdf_file_path)
  default_rviz_config_path = os.path.join(pkg_share, rviz_config_file_path)
  world_path = os.path.join(FindPackageShare(package='hunter2_gazebo').find('hunter2_gazebo'), world_file_path)
  
  gazebo_models_path = os.path.join(pkg_share, gazebo_models_path)
  os.environ["IGN_GAZEBO_RESOURCE_PATH"] = gazebo_models_path
 
  # Launch configuration variables specific to simulation
  use_sim_time = LaunchConfiguration('use_sim_time', default='true')
  gui = LaunchConfiguration('gui')
  headless = LaunchConfiguration('headless')
  namespace_1 = LaunchConfiguration('namespace_1')
  namespace_2 = LaunchConfiguration('namespace_2')
  namespace_3 = LaunchConfiguration('namespace_3')
  rviz_config_file = LaunchConfiguration('rviz_config_file')
  urdf_model = LaunchConfiguration('urdf_model')
  use_namespace = LaunchConfiguration('use_namespace')
  use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
  use_rviz = LaunchConfiguration('use_rviz')
  use_simulator = LaunchConfiguration('use_simulator')
  world = LaunchConfiguration('world')
 
  # Declare the launch arguments  
  declare_use_sim_time_cmd = DeclareLaunchArgument(
    name='use_sim_time',
    default_value='True',
    description='Use simulation (Gazebo) clock if true')

  declare_use_joint_state_publisher_cmd = DeclareLaunchArgument(
    name='gui',
    default_value='True',
    description='Flag to enable joint_state_publisher_gui')
 
  declare_namespace_cmd = DeclareLaunchArgument(
    name='namespace_1',
    default_value='robot1',
    description='Top-level namespace')
 
  declare_use_namespace_cmd = DeclareLaunchArgument(
    name='use_namespace',
    default_value='False',
    description='Whether to apply a namespace to the navigation stack')
 
  declare_rviz_config_file_cmd = DeclareLaunchArgument(
    name='rviz_config_file',
    default_value=default_rviz_config_path,
    description='Full path to the RVIZ config file to use')
 
  declare_simulator_cmd = DeclareLaunchArgument(
    name='headless',
    default_value='False',
    description='Whether to execute gzclient')
 
  declare_urdf_model_path_cmd = DeclareLaunchArgument(
    name='urdf_model', 
    default_value=default_urdf_model_path, 
    description='Absolute path to robot urdf file')
 
  declare_use_robot_state_pub_cmd = DeclareLaunchArgument(
    name='use_robot_state_pub',
    default_value='True',
    description='Whether to start the robot state publisher')
 
  declare_use_rviz_cmd = DeclareLaunchArgument(
    name='use_rviz',
    default_value='False',
    description='Whether to start RVIZ')
 
  declare_use_simulator_cmd = DeclareLaunchArgument(
    name='use_simulator',
    default_value='True',
    description='Whether to start the simulator')
 
  declare_world_cmd = DeclareLaunchArgument(
    name='world',
    default_value=world_path,
    description='Full path to the world model file to load')

  declare_namespace_2_cmd = DeclareLaunchArgument(
    name='namespace_2',
    default_value='robot2',
    description='Namespace for the second robot')

  declare_namespace_3_cmd = DeclareLaunchArgument(
    name='namespace_3',
    default_value='robot3',
    description='Namespace for the third robot')
  
    
  # Launch RViz
  start_rviz_cmd = Node(
    package='rviz2',
    executable='rviz2',
    name='rviz2',
    condition=IfCondition(use_rviz),
    output='screen',
    arguments=['-d', rviz_config_file])
 
 
  # Start Gazebo server - with -r flag to start running (not paused)
  start_ign_gazebo = ExecuteProcess(
    cmd=['ign', 'gazebo', '-r', LaunchConfiguration('world')],
    condition=IfCondition(PythonExpression([use_simulator, ' and not ', headless])),
    output='screen'
  )
  
  # Launch the robot
  spawn_entity_cmd_1 = Node(
    package='ros_gz_sim',
    executable='create',
    arguments=[
        '-name', 'robot1',
        '-topic', PathJoinSubstitution([
            '/', LaunchConfiguration('namespace_1'), 'robot_description'
        ]),
        '-x', spawn_x_val,
        '-y', spawn_y_val,
        '-z', spawn_z_val,
        '-Y', spawn_yaw_val
    ],
    namespace=LaunchConfiguration('namespace_1'),
    output='screen'
  )
  
  # Launch the robot
  spawn_entity_cmd_2 = Node(
    package='ros_gz_sim',
    executable='create',
    arguments=[
        '-name', 'robot2',
        '-topic', PathJoinSubstitution([
            '/', LaunchConfiguration('namespace_2'), 'robot_description'
        ]),
        '-x', spawn_x_val_2,
        '-y', spawn_y_val,
        '-z', spawn_z_val,
        '-Y', spawn_yaw_val
    ],
    namespace=LaunchConfiguration('namespace_2'),
    output='screen'
  )
  
  # Launch the robot
  spawn_entity_cmd_3 = Node(
    package='ros_gz_sim',
    executable='create',
    arguments=[
        '-name', 'robot3',
        '-topic', PathJoinSubstitution([
            '/', LaunchConfiguration('namespace_3'), 'robot_description'
        ]),
        '-x', spawn_x_val_3,
        '-y', spawn_y_val,
        '-z', spawn_z_val,
        '-Y', spawn_yaw_val
    ],
    namespace=LaunchConfiguration('namespace_3'),
    output='screen'
  )
  
  
  # Subscribe to the joint states of the robot, and publish the 3D pose of each link.    
  start_robot_state_publisher_cmd = Node(
    package='robot_state_publisher',
    executable='robot_state_publisher',
    parameters=[{
        'robot_description': launch_ros.descriptions.ParameterValue(
            launch.substitutions.Command([
                'xacro ', os.path.join(pkg_share, urdf_file_path)
            ]),
            value_type=str
        ),
       # 'frame_prefix': 'robot1/'  # Add namespace as prefix
    }],
    namespace=LaunchConfiguration('namespace_1'),
    output='screen'
  )

  start_robot_state_publisher_cmd_2 = Node(
    package='robot_state_publisher',
    executable='robot_state_publisher',
    parameters=[{
        'robot_description': launch_ros.descriptions.ParameterValue(
            launch.substitutions.Command([
                'xacro ', os.path.join(pkg_share, urdf_file_path_2)
            ]),
            value_type=str
        ),
        #'frame_prefix': 'robot2/'  # Add namespace as prefix
    }],
    namespace=LaunchConfiguration('namespace_2'),
    output='screen'
  )
  
  start_robot_state_publisher_cmd_3 = Node(
    package='robot_state_publisher',
    executable='robot_state_publisher',
    parameters=[{
        'robot_description': launch_ros.descriptions.ParameterValue(
            launch.substitutions.Command([
                'xacro ', os.path.join(pkg_share, urdf_file_path_3)
            ]),
            value_type=str
        ),
        #'frame_prefix': 'robot2/'  # Add namespace as prefix
    }],
    namespace=LaunchConfiguration('namespace_3'),
    output='screen'
  )

  
  # Publish the joint states of the robot
  start_joint_state_publisher_cmd = Node(
    package='joint_state_publisher',
    executable='joint_state_publisher',
    name='joint_state_publisher',
    condition=UnlessCondition(gui),
    parameters=[{'use_sim_time': use_sim_time}],
    namespace=LaunchConfiguration('namespace_1'))
  
  
  start_joint_state_publisher_cmd_2 = Node(
    package='joint_state_publisher',
    executable='joint_state_publisher',
    name='joint_state_publisher',
    condition=UnlessCondition(gui),
    parameters=[{'use_sim_time': use_sim_time}],
    namespace=LaunchConfiguration('namespace_2'))
    

  start_joint_state_publisher_cmd_3 = Node(
    package='joint_state_publisher',
    executable='joint_state_publisher',
    name='joint_state_publisher',
    condition=UnlessCondition(gui),
    parameters=[{'use_sim_time': use_sim_time}],
    namespace=LaunchConfiguration('namespace_3'))

  


  # Create the launch description and populate
  ld = LaunchDescription()
 
  # Declare the launch options
  ld.add_action(declare_use_sim_time_cmd)
  ld.add_action(declare_use_joint_state_publisher_cmd)
  ld.add_action(declare_namespace_cmd)
  ld.add_action(declare_use_namespace_cmd)
  ld.add_action(declare_rviz_config_file_cmd)
  ld.add_action(declare_simulator_cmd)
  ld.add_action(declare_urdf_model_path_cmd)
  ld.add_action(declare_use_robot_state_pub_cmd)  
  ld.add_action(declare_use_rviz_cmd) 
  ld.add_action(declare_use_simulator_cmd)
  ld.add_action(declare_world_cmd)
  ld.add_action(declare_namespace_2_cmd)
  ld.add_action(declare_namespace_3_cmd)
  
 
  # ld.add_action(controller)


 
  # Add any actions
  ld.add_action(start_ign_gazebo)
  ld.add_action(spawn_entity_cmd_1)
  ld.add_action(spawn_entity_cmd_2)
  ld.add_action(spawn_entity_cmd_3)
  ld.add_action(start_robot_state_publisher_cmd)
  ld.add_action(start_robot_state_publisher_cmd_2)
  ld.add_action(start_robot_state_publisher_cmd_3)
  ld.add_action(start_joint_state_publisher_cmd)
  ld.add_action(start_joint_state_publisher_cmd_2)
  ld.add_action(start_joint_state_publisher_cmd_3)

  
  # ld.add_action(start_dummy_sensors)
  ld.add_action(start_rviz_cmd)

  # ROS-Gazebo bridge for LiDAR sensor data - all three robots
  bridge_cmd = ExecuteProcess(
    cmd=[
      'ros2', 'run', 'ros_gz_bridge', 'parameter_bridge',
      # Robot 1 PointCloud2
      '/world/default/model/robot1/link/base_link/sensor/laser/scan/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked',
      # Robot 2 PointCloud2  
      '/world/default/model/robot2/link/base_link/sensor/laser/scan/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked',
      # Robot 3 PointCloud2
      '/world/default/model/robot3/link/base_link/sensor/laser/scan/points@sensor_msgs/msg/PointCloud2@gz.msgs.PointCloudPacked',
      # Robot 1 cmd_vel
      '/model/robot1/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
      # Robot 2 cmd_vel
      '/model/robot2/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
      # Robot 3 cmd_vel
      '/model/robot3/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
      # Clock for simulation time
      '/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock',
      '--ros-args',
      # Remappings for all three robots
      '-r', '/world/default/model/robot1/link/base_link/sensor/laser/scan/points:=/robot1/scan/points',
      '-r', '/world/default/model/robot2/link/base_link/sensor/laser/scan/points:=/robot2/scan/points', 
      '-r', '/world/default/model/robot3/link/base_link/sensor/laser/scan/points:=/robot3/scan/points',
      # Remap cmd_vel topics
      '-r', '/model/robot1/cmd_vel:=/robot1/cmd_vel',
      '-r', '/model/robot2/cmd_vel:=/robot2/cmd_vel',
      '-r', '/model/robot3/cmd_vel:=/robot3/cmd_vel'
    ],
    output='screen'
  )
  
  ld.add_action(bridge_cmd)
 
  return ld
