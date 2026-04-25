# ur12e_hande_moveit.launch.py
# Custom MoveIt2 launch with ur_manipulator + hand_e planning groups.
print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from moveit_configs_utils import MoveItConfigsBuilder


def launch_setup(context, *args, **kwargs):
    robot_ip    = LaunchConfiguration("robot_ip").perform(context)
    launch_rviz = LaunchConfiguration("launch_rviz").perform(context)

    moveit_config = (
        MoveItConfigsBuilder("ur12e_hande", package_name="ur12e_hande_bringup")
        .robot_description(
            file_path="urdf/ur12e_hande.urdf.xacro",
            mappings={
                "robot_ip":             robot_ip,
                "use_mock_hardware":    "false",
                "mock_sensor_commands": "false",
                "headless_mode":        "true",
            },
        )
        .robot_description_semantic(file_path="config/moveit/ur12e_hande.srdf")
        .robot_description_kinematics(file_path="config/moveit/kinematics.yaml")
        .trajectory_execution(file_path="config/moveit/moveit_controllers.yaml")
        .planning_pipelines(pipelines=["ompl", "pilz_industrial_motion_planner"])
        .to_moveit_configs()
    )

    move_group = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict()],
    )

    rviz_config = PathJoinSubstitution([
        FindPackageShare("ur_moveit_config"), "config", "moveit.rviz"
    ])
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2_moveit",
        output="log",
        arguments=["-d", rviz_config],
        condition=IfCondition(launch_rviz),
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
        ],
    )

    return [move_group, rviz_node]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("robot_ip",    default_value="10.18.1.106",
                              description="UR12e IP address"),
        DeclareLaunchArgument("launch_rviz", default_value="true",
                              description="Launch RViz with MoveIt"),
        OpaqueFunction(function=launch_setup),
    ])
