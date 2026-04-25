#!/usr/bin/env python3
# hande_gripper_node.py — Robotiq Hand-E ROS2 action server via socket API (port 63352)
# Exposes /gripper_action_controller/gripper_cmd (control_msgs/GripperCommand)
print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

import socket
import time
import rclpy
from rclpy.node import Node
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from control_msgs.action import GripperCommand
from sensor_msgs.msg import JointState

GRIPPER_PORT  = 63352
POS_MAX_M     = 0.025   # 0.025 m = fully open
GOAL_TOL      = 0.001   # 1 mm tolerance


class HandeGripperNode(Node):
    def __init__(self):
        super().__init__('hande_gripper_node')

        self.declare_parameter('robot_ip', '10.18.1.106')
        self.declare_parameter('timeout',  2.0)

        self._ip      = self.get_parameter('robot_ip').value
        self._timeout = self.get_parameter('timeout').value
        self._pos_m   = 0.0

        self._activate()
        self._pos_m = self._get_position()

        self._js_pub = self.create_publisher(JointState, 'joint_states', 10)
        self.create_timer(0.05, self._publish_joint_state)  # 20 Hz

        self._action_server = ActionServer(
            self,
            GripperCommand,
            'gripper_action_controller/gripper_cmd',
            execute_callback=self._execute,
            goal_callback=lambda _: GoalResponse.ACCEPT,
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            callback_group=ReentrantCallbackGroup(),
        )

        self.get_logger().info(f'Hand-E node ready — {self._ip}:{GRIPPER_PORT}')

    def _publish_joint_state(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name     = ['hande_robotiq_hande_left_finger_joint',
                        'hande_robotiq_hande_right_finger_joint']
        msg.position = [self._pos_m, self._pos_m]
        msg.velocity = [0.0, 0.0]
        msg.effort   = [0.0, 0.0]
        self._js_pub.publish(msg)

    # ── socket helpers ────────────────────────────────────────────────────────

    def _send(self, cmds: list[bytes]):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self._timeout)
            s.connect((self._ip, GRIPPER_PORT))
            for c in cmds:
                s.sendall(c)
                time.sleep(0.05)

    def _query(self, cmd: bytes) -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self._timeout)
            s.connect((self._ip, GRIPPER_PORT))
            s.sendall(cmd)
            return s.recv(64).decode().strip()

    # ── gripper protocol ──────────────────────────────────────────────────────

    def _activate(self):
        try:
            self._send([
                b'SET ACT 1\n',
                b'SET MOD 0\n',
                b'SET GTO 1\n',
                b'SET SPE 255\n',
                b'SET FOR 255\n',
            ])
            self.get_logger().info('Gripper activated')
        except Exception as e:
            self.get_logger().warn(f'Gripper activation error: {e}')

    def _metres_to_raw(self, m: float) -> int:
        m = max(0.0, min(POS_MAX_M, m))
        return int((1.0 - m / POS_MAX_M) * 255)   # 0 m = 255 (closed), 0.025 m = 0 (open)

    def _raw_to_metres(self, raw: int) -> float:
        return (1.0 - raw / 255.0) * POS_MAX_M

    def _set_position(self, m: float):
        raw = self._metres_to_raw(m)
        self._send([b'SET GTO 1\n', f'SET POS {raw}\n'.encode()])

    def _get_position(self) -> float:
        try:
            resp = self._query(b'GET POS\n')   # returns "POS <0-255>"
            raw  = int(resp.split()[-1])
            return self._raw_to_metres(raw)
        except Exception:
            return self._pos_m

    def _is_moving(self) -> bool:
        try:
            resp = self._query(b'GET STA\n')   # "STA 0" = moving, "STA 3" = reached
            return resp.split()[-1] == '0'
        except Exception:
            return False

    # ── action ────────────────────────────────────────────────────────────────

    def _execute(self, goal_handle):
        target  = goal_handle.request.command.position
        self.get_logger().info(f'Goal: {target:.4f} m')

        self._set_position(target)

        feedback = GripperCommand.Feedback()
        for _ in range(50):   # max 5 s wait
            time.sleep(0.1)
            if goal_handle.is_cancel_requested:
                self._set_position(self._pos_m)
                goal_handle.canceled()
                return GripperCommand.Result()

            self._pos_m  = self._get_position()
            feedback.position      = self._pos_m
            feedback.reached_goal  = abs(self._pos_m - target) < GOAL_TOL
            feedback.stalled       = False
            goal_handle.publish_feedback(feedback)

            if not self._is_moving():
                break

        self._pos_m = self._get_position()
        reached     = abs(self._pos_m - target) < GOAL_TOL

        result           = GripperCommand.Result()
        result.position  = self._pos_m
        result.effort    = goal_handle.request.command.max_effort
        result.reached_goal = reached
        result.stalled   = False

        goal_handle.succeed()
        self.get_logger().info(f'Done: pos={self._pos_m:.4f} m, reached={reached}')
        return result


def main():
    rclpy.init()
    node = HandeGripperNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
