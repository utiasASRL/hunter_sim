import os
import os.path as osp
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
import shutil
from rclpy.exceptions import ParameterException

import yaml

def generate_robot_yaml(num_robots, spacing, output_filename="robot_config.yaml"):
    """
    Generates a ROS YAML configuration file for a variable number of robots.
    
    :param num_robots: Total number of robots (including robot0)
    :param spacing: The follow_distance increment per robot
    :param output_filename: The name of the output YAML file
    """
    config_data = {}

    # 1. Generate configuration for follower robots (robot1 to robot[N-1])
    for i in range(1, num_robots):
        node_name = f'/robot{i}/vtr/navigator'
        config_data[node_name] = {
            'ros__parameters': {
                'path_planning': {
                    'bicycle_mpc_follower': {
                        'leader_namespace': '/robot0',
                        'follow_distance': float(i * spacing)
                    }
                }
            }
        }

    # 2. Generate convoy planning node for all robots (robot0 to robot[N-1])
    convoy_robots = {}
    for i in range(num_robots):
        convoy_robots[f'robot{i}'] = {
            'leader_mpc': 'bicycle_mpc',
            'follower_mpc': 'bicycle_mpc_follower'
        }

    config_data['/vtr/convoy_planning_node'] = {
        'ros__parameters': convoy_robots
    }

    # 3. Write to file
    # default_flow_style=False ensures the block formatting (not inline JSON-like)
    # sort_keys=False maintains the insertion order 
    with open(output_filename, 'w') as yaml_file:
        yaml.dump(
            config_data, 
            yaml_file, 
            default_flow_style=False, 
            sort_keys=False
        )

def add_robots(context, *args, **kwargs):
    num_robots = int(LaunchConfiguration('num_robots').perform(context))
    spacing = float(LaunchConfiguration('robot_spacing').perform(context))
    pose_graph_folder = LaunchConfiguration('pose_graph').perform(context)

    config_dir = osp.join(os.getenv('VTRROOT'), 'hunter_sim', 'src', 'hunter_sim', 'vtr_hunter', 'config', 'lidar_hunter.yaml')

    if osp.basename(pose_graph_folder) != 'graph':
        raise ParameterException("pose_graph must point to a folder with the name graph")
        
    nodes_to_launch = []
    os.makedirs("/tmp/vtr", exist_ok=True)
    generate_robot_yaml(num_robots, spacing, output_filename="/tmp/vtr/convoy_config.yaml")

    
    for i in range(num_robots):
        shutil.copytree(pose_graph_folder, f'/tmp/vtr/robot{i}/graph', dirs_exist_ok=True)

        nodes_to_launch.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([
                    get_package_share_directory('vtr_hunter'),
                    "launch", 
                    "vtr_sim.launch.py" 
                ])
            ),
            launch_arguments={ 
                'robot_name': f'robot{i}',
                'planner': 'dynamic_path_planner',
                'base_params': config_dir, 
                'data_dir': f'/tmp/vtr/robot{i}',
                'override_params': f'/tmp/vtr/convoy_config.yaml'
            }.items()
        ))


    return nodes_to_launch

def generate_launch_description():

    robot_count = DeclareLaunchArgument(
        'num_robots', default_value="1"
    )

    robot_spacing = DeclareLaunchArgument(
        'robot_spacing', default_value="2.0"
    )

    pose_graph_folder = DeclareLaunchArgument(
        'pose_graph',
        description="A path to a pose graph of form /a/path/graph"
    )

    start_vtr_sessions = OpaqueFunction(function=add_robots)
   

    return LaunchDescription([
        robot_count,
        robot_spacing,
        pose_graph_folder,
        start_vtr_sessions
    ])