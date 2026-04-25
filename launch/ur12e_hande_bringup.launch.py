# ur12e_hande_bringup.launch.py
# Real-hardware bringup: delegates arm control to ur_robot_driver,
# adds Robotiq Hand-E on its own controller_manager namespace.

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, OpaqueFunction,
    IncludeLaunchDescription, TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def launch_setup(context, *args, **kwargs):
    robot_ip        = LaunchConfiguration("robot_ip").perform(context)
    tf_prefix       = LaunchConfiguration("tf_prefix").perform(context)
    tty_port        = LaunchConfiguration("tty_port").perform(context)
    create_socat    = LaunchConfiguration("create_socat_tty").perform(context)
    launch_rviz     = LaunchConfiguration("launch_rviz")
    launch_moveit   = LaunchConfiguration("launch_moveit")

    bringup_pkg  = FindPackageShare("ur12e_hande_bringup")
    ur_driver_pkg = FindPackageShare("ur_robot_driver")

    # Combined URDF (real hardware mode)
    robot_description = ParameterValue(Command([
        "xacro ",
        PathJoinSubstitution([bringup_pkg, "urdf", "ur12e_hande.urdf.xacro"]),
        " use_mock_hardware:=false",
        " robot_ip:=", robot_ip,
        " tf_prefix:=", tf_prefix,
        " tty_port:=", tty_port,
        " create_socat_tty:=", create_socat,
        " socat_ip_address:=", robot_ip,
    ]), value_type=str)

    # ── UR arm — delegate to ur_robot_driver ───────────────────────────────
    # ur_control.launch.py handles: URScript server, dashboard, scaled controller, JSB
    ur_control = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([ur_driver_pkg, "launch", "ur_control.launch.py"])
        ]),
        launch_arguments={
            "ur_type":              "ur12e",
            "robot_ip":             robot_ip,
            "tf_prefix":            tf_prefix,
            "launch_rviz":          "false",   # we handle RViz below
            "headless_mode":        "false",
            "use_fake_hardware":    "false",
            "activate_joint_controller": "true",
            "initial_joint_controller": "scaled_joint_trajectory_controller",
        }.items(),
    )

    # ── Robotiq Hand-E gripper — separate controller_manager namespace ─────
    # RSP in the gripper namespace publishes to /gripper/robot_description,
    # which is exactly where the gripper controller_manager looks for it.
    gripper_rsp = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        namespace="gripper",
        parameters=[{"robot_description": robot_description}],
        remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
    )

    gripper_control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        namespace="gripper",
        parameters=[
            {"robot_description": robot_description},
            PathJoinSubstitution([bringup_pkg, "config", "ur12e_hande_controllers.yaml"]),
        ],
    )

    gripper_jsb_spawner = TimerAction(
        period=3.0,
        actions=[Node(
            package="controller_manager",
            executable="spawner",
            arguments=["gripper_action_controller", "-c", "/gripper/controller_manager"],
        )],
    )

    # ── optional MoveIt2 ───────────────────────────────────────────────────
    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare("ur_moveit_config"), "launch", "ur_moveit.launch.py"
            ])
        ]),
        launch_arguments={
            "ur_type":           "ur12e",
            "robot_ip":          robot_ip,
            "launch_rviz":       "false",
            "use_fake_hardware": "false",
        }.items(),
        condition=IfCondition(launch_moveit),
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        condition=IfCondition(launch_rviz),
    )

    return [
        ur_control,
        gripper_rsp,
        gripper_control_node,
        gripper_jsb_spawner,
        moveit,
        rviz_node,
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("robot_ip",       default_value="10.18.1.106",
                              description="UR12e IP address"),
        DeclareLaunchArgument("tf_prefix",      default_value="",
                              description="TF prefix for all joints"),
        DeclareLaunchArgument("tty_port",       default_value="/tmp/ttyUR",
                              description="Serial port for Hand-E (real hw)"),
        DeclareLaunchArgument("create_socat_tty", default_value="false",
                              description="Create socat TTY tunnel to robot"),
        DeclareLaunchArgument("launch_rviz",    default_value="true",
                              description="Launch RViz"),
        DeclareLaunchArgument("launch_moveit",  default_value="false",
                              description="Launch MoveIt2 move_group"),
        OpaqueFunction(function=launch_setup),
    ])
