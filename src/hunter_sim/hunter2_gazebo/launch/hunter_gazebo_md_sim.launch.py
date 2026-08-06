import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.actions import IncludeLaunchDescription, AppendEnvironmentVariable, DeclareLaunchArgument, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def add_robots(context, *args, **kwargs):
    num_robots = int(LaunchConfiguration('num_robots').perform(context))
    robot_offset = float(LaunchConfiguration('robot_spacing').perform(context))

    COLORS = [  "0.00 0.90 1.00 1",
                "1.00 0.10 0.60 1",
                "0.30 1.00 0.10 1",
                "1.00 0.90 0.00 1",
                "1.00 0.45 0.00 1",
                "0.00 0.40 1.00 1",
                "0.70 0.10 1.00 1",
                "1.00 0.00 1.00 1",
                "0.75 1.00 0.00 1",
                "0.00 0.85 0.40 1",
                "1.00 0.15 0.00 1"
                ]
        
    nodes_to_launch = []
    
    for i in range(num_robots):
        nodes_to_launch.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([
                    get_package_share_directory('hunter2_gazebo'),
                    "launch", 
                    "hunter_spawn.launch.py" 
                ])
            ),
            launch_arguments={ 
                'robot_name': f'robot{i}',
                'robot_colour': COLORS[i % len(COLORS)],
                'start_x': f'{(num_robots - 1 - i) * robot_offset}' 
            }.items()
        ))


    return nodes_to_launch

def generate_launch_description():

    robot_count = DeclareLaunchArgument(
        'num_robots', default_value="1"
    )

    robot_offset = DeclareLaunchArgument(
        'robot_spacing', default_value="1"
    )

    # 1. Paths and Definitions   
    hunter_base_pkg_share = get_package_share_directory('hunter2_base')
    hunter_gazebo_pkg_share = get_package_share_directory('hunter2_gazebo')

    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')

    add_hunter2_base_path = AppendEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=os.path.dirname(hunter_base_pkg_share)
    )
    add_hunter2_gazebo_path = AppendEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=os.path.dirname(hunter_gazebo_pkg_share)
    )

    # 2. Start Gazebo
    gz_server = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f"-r {os.path.join(hunter_gazebo_pkg_share, 'world', 'mars_dome.world')}"}.items(),
    )

    base_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
        ],
        output='screen'
    )

    spawn_robots = OpaqueFunction(function=add_robots)
   

    return LaunchDescription([
        robot_count,
        robot_offset,
        add_hunter2_base_path,
        add_hunter2_gazebo_path,
        gz_server,
        base_bridge,
        spawn_robots
    ])