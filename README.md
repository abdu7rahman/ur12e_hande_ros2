# ur12e_hande_ros2

ROS2 Jazzy bringup package for the **UR12e arm + Robotiq Hand-E gripper**. Wraps the official `ur_robot_driver` for the arm and the AGH-CEAI `robotiq_hande_driver` for the gripper into a single pluggable launch system.

---

## Dependencies

### apt

```bash
sudo apt install ros-jazzy-ur libmodbus-dev
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

> The `PATH` prefix is needed if you have Python 3.13 (managed by uv) installed — it forces CMake to use the system Python that has `catkin_pkg`.

---

## Simulation (no robot needed)

Runs both arm and gripper in fake hardware mode via a single `controller_manager`.

```bash
ros2 launch ur12e_hande_bringup ur12e_hande_sim.launch.py
```

### RViz setup

Once launched, open RViz and:
1. Set **Fixed Frame** → `world`
2. Add → **RobotModel** → set **Description Topic** to `/robot_description`
3. Add → **TF**

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
  control_msgs/action/GripperCommand \
  "{command: {position: 0.025, max_effort: 5.0}}"

# Close
ros2 action send_goal /gripper_action_controller/gripper_cmd \
  control_msgs/action/GripperCommand \
  "{command: {position: 0.0, max_effort: 5.0}}"
```

### Verify all controllers are active

```bash
ros2 control list_controllers
# expected: joint_state_broadcaster, joint_trajectory_controller, gripper_action_controller — all active

ros2 topic echo /joint_states --once
# expected: 7 joints (6 arm + 1 gripper finger)
```

---

## Real Hardware

### Prerequisites

1. Robot booted and reachable on the network — verify with `ping 10.18.1.106`
2. Teach pendant set to **Remote Control** mode
3. **External Control** URCap installed on the robot, configured with your PC's IP
4. Hand-E gripper plugged into the robot's tool communication port (RS-485)

### Launch

```bash
ros2 launch ur12e_hande_bringup ur12e_hande_bringup.launch.py \
  robot_ip:=10.18.1.106 \
  create_socat_tty:=true \
  launch_rviz:=true
```

**After launch**, hit **Play** on the External Control program on the teach pendant — the driver will not connect until the program is running.

### Optional: launch with MoveIt2

```bash
ros2 launch ur12e_hande_bringup ur12e_hande_bringup.launch.py \
  robot_ip:=10.18.1.106 \
  create_socat_tty:=true \
  launch_moveit:=true
```

### Test arm (real hardware)

Real hardware uses `scaled_joint_trajectory_controller` which respects the speed scaling slider on the pendant.

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
  control_msgs/action/GripperCommand \
  "{command: {position: 0.025, max_effort: 5.0}}"

# Close
ros2 action send_goal /gripper_action_controller/gripper_cmd \
  control_msgs/action/GripperCommand \
  "{command: {position: 0.0, max_effort: 5.0}}"
```

### Verify connection

```bash
ros2 control list_controllers        # all controllers active
ros2 topic hz /joint_states          # ~500 Hz from real robot
```

---

## Launch Arguments

| Argument | Default | Description |
|---|---|---|
| `robot_ip` | `10.18.1.106` | UR12e IP address |
| `tf_prefix` | `""` | TF prefix for all joints |
| `tty_port` | `/tmp/ttyUR` | Serial port for Hand-E |
| `create_socat_tty` | `false` | Tunnel gripper RS-485 over TCP via socat |
| `launch_rviz` | `true` | Launch RViz |
| `launch_moveit` | `false` | Launch MoveIt2 move_group |

---

## Package Structure

```
ur12e_hande_bringup/
├── urdf/
│   └── ur12e_hande.urdf.xacro      # combined arm + gripper URDF
├── launch/
│   ├── ur12e_hande_sim.launch.py   # sim / fake hardware
│   └── ur12e_hande_bringup.launch.py  # real hardware
└── config/
    ├── ur12e_hande_controllers.yaml
    └── moveit/
        ├── kinematics.yaml
        └── moveit_controllers.yaml
```

---

## License

MIT — Mohammed Abdul Rahman, Northeastern University Seattle
