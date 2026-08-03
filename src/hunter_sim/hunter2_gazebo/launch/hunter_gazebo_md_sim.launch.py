import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.actions import IncludeLaunchDescription, AppendEnvironmentVariable, SetEnvironmentVariable, DeclareLaunchArgument, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource


def add_robots(context, *args, **kwargs):
    mode_value = int(LaunchConfiguration('num_robots').perform(context))

    COLORS = ["0.0 0.819 0.93 1",
              "0.85 0.58 0.61 1",
              "0.56 0.59 0.47 1",
              "0.96 0.88 0.71 1",
              "0.93 0.66 0.56 1",
              "0.71 0.82 0.89 1",
              "0.73 0.61 0.76 1",
              "0.40 0.33 0.37 1",
              "1.00 0.98 0.59 1",
              "0.42 0.56 0.14 1",
              "0.64 0.57 0.57 1"]
        
    nodes_to_launch = []
    
    for i in range(mode_value):
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
                'start_x': f'{5*i}' 
            }.items()
        ))


    return nodes_to_launch

def generate_launch_description():

    robot_count = DeclareLaunchArgument(
        'num_robots', default_value="1"
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

    spawn_robots = OpaqueFunction(function=add_robots)
   

    return LaunchDescription([
        robot_count,
        add_hunter2_base_path,
        add_hunter2_gazebo_path,
        gz_server,
        spawn_robots
    ])