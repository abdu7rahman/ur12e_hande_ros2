# ur12e_hande_sim.launch.py
# Fake-hardware bringup: arm + Hand-E gripper, no physical robot needed.
# Uses a single controller_manager with mock_components for both devices.

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch_ros.parameter_descriptions import ParameterValue


def launch_setup(context, *args, **kwargs):
    tf_prefix       = LaunchConfiguration("tf_prefix").perform(context)
    launch_rviz     = LaunchConfiguration("launch_rviz")

    pkg = FindPackageShare("ur12e_hande_bringup")

    robot_description = ParameterValue(Command([
        "xacro ",
        PathJoinSubstitution([pkg, "urdf", "ur12e_hande.urdf.xacro"]),
        " use_mock_hardware:=true",
        " mock_sensor_commands:=false",
        " tf_prefix:=", tf_prefix,
    ]), value_type=str)

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description, "use_sim_time": False}],
        remappings=[("/tf", "tf"), ("/tf_static", "tf_static")],
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            {"robot_description": robot_description},
            PathJoinSubstitution([pkg, "config", "ur12e_hande_controllers.yaml"]),
        ],
    )

    jsb_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "-c", "/controller_manager"],
    )

    arm_spawner = TimerAction(
        period=2.0,
        actions=[Node(
            package="controller_manager",
            executable="spawner",
            arguments=["joint_trajectory_controller", "-c", "/controller_manager"],
        )],
    )

    gripper_spawner = TimerAction(
        period=2.5,
        actions=[Node(
            package="controller_manager",
            executable="spawner",
            arguments=["gripper_action_controller", "-c", "/controller_manager"],
        )],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        condition=IfCondition(launch_rviz),
    )

    return [
        robot_state_publisher,
        control_node,
        jsb_spawner,
        arm_spawner,
        gripper_spawner,
        rviz_node,
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("tf_prefix",   default_value="",     description="TF prefix"),
        DeclareLaunchArgument("launch_rviz", default_value="true", description="Launch RViz"),
        OpaqueFunction(function=launch_setup),
    ])
