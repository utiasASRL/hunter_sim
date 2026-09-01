import os
import os.path as osp

from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch import LaunchDescription
from launch_ros.actions import Node
import yaml
from rclpy.exceptions import ParameterException


ROBOT_NAME_STR = "robot_name"

def setup_vtr(context, *args, **kwargs):
    robot_name = LaunchConfiguration(ROBOT_NAME_STR).perform(context)
    pose_graph_dir = LaunchConfiguration("data_dir").perform(context)
 

    # config directory
    config_dir = osp.join(os.getenv('VTRSRC'), 'config')
    temp_dir = os.getenv('VTRTEMP')

    if pose_graph_dir == "":
        with open(osp.join(temp_dir, 'setup_params.yaml')) as setup_file:
            try:
                config_data = yaml.safe_load(setup_file)
                pose_graph_dir = config_data['/**']['ros__parameters']['data_dir']
            except yaml.YAMLError:
                raise ParameterException("No pose graph specified through UI or launch argument.")

    vtr_node = Node(
        package='vtr_navigation',
        namespace=f'/{robot_name}/vtr',
        executable='vtr_navigation',
        output='screen',
        remappings=[("command", f'/{robot_name}/cmd_vel')],
        parameters=[
            PathJoinSubstitution((config_dir, LaunchConfiguration("base_params"))),
            {
                "robot_frame": f"{robot_name}/base_link",
                "lidar_frame": f"{robot_name}/lidar_link",
                "lidar_topic": f"/{robot_name}/scan/points",
                "data_dir": pose_graph_dir,
                "model_dir": LaunchConfiguration("model_dir"),
                "start_new_graph": LaunchConfiguration("start_new_graph"),
                "use_sim_time": True,
                "path_planning.type": LaunchConfiguration("planner"),
                "path_planning.stationary.type": "stationary",
            },
            PathJoinSubstitution((config_dir, LaunchConfiguration("override_params")))
        ],
    )

    return [vtr_node]

def generate_launch_description():
    
    return LaunchDescription([
        DeclareLaunchArgument(ROBOT_NAME_STR, default_value="robot"),
        DeclareLaunchArgument('data_dir', default_value='', description='directory to store graph, if blank use setup UI'),
        DeclareLaunchArgument('model_dir', default_value="", description='model directory (folder for PyTorch .pt models)'),
        DeclareLaunchArgument('start_new_graph', default_value='false', description='whether to start a new pose graph'),
        DeclareLaunchArgument('planner', default_value='cbit', description='use no planner. Publish zero'),
        DeclareLaunchArgument('base_params', description='base parameter file (sensor, robot specific)'),
        DeclareLaunchArgument('override_params', default_value='', description='scenario specific parameter overrides'),
        OpaqueFunction(function=setup_vtr)
    ])
