# ur12e_hande_bringup.launch.py
# Real-hardware bringup: delegates arm control to ur_robot_driver,
# adds Robotiq Hand-E on its own controller_manager namespace.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    robot_ip      = LaunchConfiguration("robot_ip").perform(context)
    tf_prefix     = LaunchConfiguration("tf_prefix").perform(context)
    launch_rviz   = LaunchConfiguration("launch_rviz").perform(context)
    launch_moveit = LaunchConfiguration("launch_moveit")

    ur_driver_pkg = FindPackageShare("ur_robot_driver")

    # ── UR arm ────────────────────────────────────────────────────────────────
    ur_control = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([ur_driver_pkg, "launch", "ur_control.launch.py"])
        ]),
        launch_arguments={
            "ur_type":                   "ur12e",
            "robot_ip":                  robot_ip,
            "tf_prefix":                 tf_prefix,
            "launch_rviz":               "false",
            "headless_mode":             "true",
            "use_fake_hardware":         "false",
            "activate_joint_controller": "true",
            "initial_joint_controller":  "scaled_joint_trajectory_controller",
        }.items(),
    )

    # ── Robotiq Hand-E gripper — socket API on port 63352 ────────────────────
    # Exposes /gripper_action_controller/gripper_cmd (GripperCommand action)
    gripper_node = Node(
        package="ur12e_hande_bringup",
        executable="hande_gripper_node.py",
        name="hande_gripper_node",
        parameters=[{"robot_ip": robot_ip}],
    )

    # ── optional MoveIt2 ──────────────────────────────────────────────────────
    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare("ur_moveit_config"), "launch", "ur_moveit.launch.py"
            ])
        ]),
        launch_arguments={
            "ur_type":           "ur12e",
            "robot_ip":          robot_ip,
            "launch_rviz":       launch_rviz,
            "use_fake_hardware": "false",
        }.items(),
        condition=IfCondition(launch_moveit),
    )

    return [ur_control, gripper_node, moveit]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("robot_ip",     default_value="10.18.1.106",
                              description="UR12e IP address"),
        DeclareLaunchArgument("tf_prefix",    default_value="",
                              description="TF prefix for all joints"),
        DeclareLaunchArgument("launch_rviz",  default_value="true",
                              description="Launch RViz"),
        DeclareLaunchArgument("launch_moveit", default_value="false",
                              description="Launch MoveIt2 move_group"),
        OpaqueFunction(function=launch_setup),
    ])
