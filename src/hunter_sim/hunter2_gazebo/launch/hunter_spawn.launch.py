import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction, DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro

def spawn_robot(context, *args, **kwargs):

    robot_ns = LaunchConfiguration('robot_name').perform(context)
    robot_colour = LaunchConfiguration('robot_colour').perform(context)
    start_x = LaunchConfiguration('start_x').perform(context)
    start_y = LaunchConfiguration('start_y').perform(context)

    # 1. Paths and Definitions
    xacro_filename = 'hunter2_gazebo_lidar.xacro'
    hunter_gazebo_pkg_share = get_package_share_directory('hunter2_gazebo')
    xacro_file = os.path.join(hunter_gazebo_pkg_share, 'xacro', xacro_filename)

    mapping = {'namespace': robot_ns,
                'body_colour': robot_colour}
    robot_desc = xacro.process_file(xacro_file, mappings=mapping).toxml()

    
    # 3. Start the Robot State Publisher
    # This broadcasts the URDF to the ROS network on the /robot_description topic
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        namespace=robot_ns,
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': True, # Crucial: tells ROS to use Gazebo's clock
            'frame_prefix': f'{robot_ns}/'
        }]
    )

    # 4. Spawn the Entity into Gazebo
    # The 'create' executable grabs the structure from /robot_description
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        namespace=robot_ns,
        arguments=[
            '-topic', 'robot_description',
            '-name', robot_ns,
            '-x', start_x,
            '-y', start_y,
            '-z', '1.0'
        ],
        output='screen'
    )

    # Remap from cmd_vel to the steering and wheel speed topics
    steering_remap_node = Node(
        package="hunter2_gazebo",
        namespace=robot_ns,
        executable='command_mapper',
        output='screen'
    )

    delayed_spawn = TimerAction(
        period=5.0,
        actions=[spawn_robot]
    )
    
    # 5. Start the ROS-Gazebo Bridge
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        namespace=robot_ns,
        arguments=[
            # Topic@ROS_Type[Direction]Gazebo_Type
            f'/{robot_ns}/steering_angle@std_msgs/msg/Float64]gz.msgs.Double',
            f'/{robot_ns}/wheel_velocity@std_msgs/msg/Float64]gz.msgs.Double',
            f'/{robot_ns}/gz_odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            f'/{robot_ns}/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
            f'/{robot_ns}/scan/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked'
        ],
        output='screen'
    )

    return [
        robot_state_publisher,
        delayed_spawn,
        steering_remap_node,
        bridge
    ]

def generate_launch_description():

    robot_ns = DeclareLaunchArgument(
        'robot_name', default_value='robot', description='Name of this unique robot'
    )

    robot_colour = DeclareLaunchArgument(
        'robot_colour', default_value="0.0 0.8196 0.9333 1"
    )

    robot_position_x = DeclareLaunchArgument(
        'start_x', default_value="0.0"
    )
    robot_position_y = DeclareLaunchArgument(
        'start_y', default_value="0.0"
    )

    delayed_spawner = OpaqueFunction(function=spawn_robot)
    

    return LaunchDescription([
        robot_ns,
        robot_colour,
        robot_position_x,
        robot_position_y,
        delayed_spawner
    ])