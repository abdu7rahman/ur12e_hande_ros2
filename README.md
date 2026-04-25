# ur12e_hande_ros2

ROS2 Jazzy bringup package for the **UR12e arm + Robotiq Hand-E gripper**. Wraps the official `ur_robot_driver` for the arm and uses a direct socket-based action server (port 63352) for the gripper — no Modbus RTU required.

---

## Dependencies

### apt

```bash
sudo apt install ros-jazzy-ur
```

### From source (clone into your workspace src/)

```bash
cd ~/ros2_ws/src
git clone https://github.com/AGH-CEAI/robotiq_hande_driver.git
git clone https://github.com/AGH-CEAI/robotiq_hande_description.git
```

---

## Build

```bash
cd ~/ros2_ws
PATH=/usr/bin:/usr/local/bin:$PATH colcon build --packages-select \
  robotiq_hande_description robotiq_hande_driver ur12e_hande_bringup
source install/setup.bash
```

> The `PATH` prefix forces CMake to use system Python if you have Python 3.13 (uv-managed) installed.

---

## Simulation (no robot needed)

```bash
ros2 launch ur12e_hande_bringup ur12e_hande_sim.launch.py
```

### Test arm (sim)

```bash
ros2 topic pub --once /joint_trajectory_controller/joint_trajectory \
  trajectory_msgs/msg/JointTrajectory \
  "{joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint],
    points: [{positions: [0.0, -1.57, 0.0, -1.57, 0.0, 0.0], time_from_start: {sec: 2}}]}"
```

### Test gripper (sim)

```bash
# Open
ros2 action send_goal /gripper_action_controller/gripper_cmd \
  control_msgs/action/GripperCommand "{command: {position: 0.025, max_effort: 5.0}}"

# Close
ros2 action send_goal /gripper_action_controller/gripper_cmd \
  control_msgs/action/GripperCommand "{command: {position: 0.0, max_effort: 5.0}}"
```

---

## Real Hardware

### Prerequisites

1. Robot reachable: `ping 10.18.1.106`
2. Teach pendant in **Remote Control** mode
3. **External Control** URCap installed and configured with your PC's IP
4. Hand-E plugged into the robot's tool communication port

### Launch (arm + gripper only)

```bash
ros2 launch ur12e_hande_bringup ur12e_hande_bringup.launch.py \
  robot_ip:=10.18.1.106
```

### Launch with MoveIt2 + RViz

```bash
ros2 launch ur12e_hande_bringup ur12e_hande_bringup.launch.py \
  robot_ip:=10.18.1.106 \
  launch_moveit:=true \
  launch_rviz:=true
```

MoveIt2 exposes two planning groups:
- `ur_manipulator` — the 6-DOF arm (use the interactive marker in RViz to set goals)
- `hand_e` — the gripper (named states: `open` / `closed`)

A floor collision plane is automatically added to the planning scene at z=0 to prevent planning below the robot's base.

### Test arm (real hardware)

```bash
ros2 action send_goal /scaled_joint_trajectory_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint],
    points: [{positions: [0.0, -1.57, 0.0, -1.57, 0.0, 0.0], time_from_start: {sec: 3}}]}}"
```

### Test gripper (real hardware)

```bash
# Open
ros2 action send_goal /gripper_action_controller/gripper_cmd \
  control_msgs/action/GripperCommand "{command: {position: 0.025, max_effort: 50.0}}"

# Close
ros2 action send_goal /gripper_action_controller/gripper_cmd \
  control_msgs/action/GripperCommand "{command: {position: 0.0, max_effort: 50.0}}"
```

### Verify

```bash
ros2 control list_controllers    # all controllers active
ros2 topic hz /joint_states      # ~500 Hz from real robot
```

---

## Architecture

```
ur12e_hande_bringup.launch.py
├── ur_control.launch.py          # ur_robot_driver (headless, Remote Control mode)
│   ├── ros2_control_node         # 500 Hz hardware interface
│   ├── joint_state_broadcaster
│   └── scaled_joint_trajectory_controller
├── hande_gripper_node.py         # socket → GripperCommand action server
│                                 # publishes joint_states for gripper fingers @ 20 Hz
└── ur12e_hande_moveit.launch.py  # (if launch_moveit:=true)
    ├── move_group                # OMPL + Pilz planners, ur_manipulator + hand_e groups
    ├── rviz2                     # MoveIt MotionPlanning panel
    └── scene_publisher.py        # adds floor plane collision object on startup
```

### Gripper protocol

The gripper node talks directly to the Hand-E's ASCII socket API on **port 63352** (no Modbus RTU, no socat):

| Command | Meaning |
|---|---|
| `SET ACT 1` | Activate |
| `SET POS <0-255>` | Move (0 = open, 255 = closed) |
| `GET POS` | Read position |
| `GET STA` | Status (0 = moving, 3 = reached) |

Position mapping: `0.0 m` = fully open, `0.025 m` = fully closed.

---

## Launch Arguments

| Argument | Default | Description |
|---|---|---|
| `robot_ip` | `10.18.1.106` | UR12e IP address |
| `tf_prefix` | `""` | TF prefix for all joints |
| `launch_rviz` | `true` | Launch RViz (with MoveIt config when `launch_moveit:=true`) |
| `launch_moveit` | `false` | Launch MoveIt2 move_group + custom SRDF |

---

## Package Structure

```
ur12e_hande_bringup/
├── urdf/
│   └── ur12e_hande.urdf.xacro         # combined arm + gripper URDF
├── launch/
│   ├── ur12e_hande_sim.launch.py      # fake hardware sim
│   ├── ur12e_hande_bringup.launch.py  # real hardware entry point
│   └── ur12e_hande_moveit.launch.py   # MoveIt2 with hand_e group
├── config/
│   ├── ur12e_hande_controllers.yaml   # ros2_control controller config
│   ├── ompl_planning.yaml
│   ├── pilz_cartesian_limits.yaml
│   └── moveit/
│       ├── ur12e_hande.srdf           # custom SRDF (ur_manipulator + hand_e)
│       ├── kinematics.yaml
│       ├── moveit_controllers.yaml    # arm JTC + gripper GripperCommand
│       ├── joint_limits.yaml          # with acceleration limits for TOTG
│       └── moveit.rviz
└── ur12e_hande_bringup/
    ├── hande_gripper_node.py          # socket-based GripperCommand action server
    └── scene_publisher.py             # adds floor plane to planning scene
```

---

## Related

- [reactive-replanning-ur12e](https://github.com/abdu7rahman/reactive-replanning-ur12e) — kinematic redundancy-based reactive replanning built on top of this package

---

## License

MIT — Mohammed Abdul Rahman, Northeastern University Seattle
