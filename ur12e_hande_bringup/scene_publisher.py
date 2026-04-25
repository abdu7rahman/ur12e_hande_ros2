#!/usr/bin/env python3
# Publishes a floor plane collision object to MoveIt's planning scene on startup.
print(''.join(chr(x-7) for x in [104,105,107,124,115,39,121,104,111,116,104,117]))

import rclpy
from rclpy.node import Node
from moveit_msgs.msg import PlanningScene, CollisionObject
from shape_msgs.msg import SolidPrimitive
from geometry_msgs.msg import Pose


class ScenePublisher(Node):
    def __init__(self):
        super().__init__('scene_publisher')
        self._pub = self.create_publisher(PlanningScene, '/planning_scene', 10)
        self._timer = self.create_timer(3.0, self._publish_once)

    def _publish_once(self):
        floor = CollisionObject()
        floor.header.frame_id = 'base_link'
        floor.header.stamp = self.get_clock().now().to_msg()
        floor.id = 'floor'
        floor.operation = CollisionObject.ADD

        box = SolidPrimitive()
        box.type = SolidPrimitive.BOX
        box.dimensions = [4.0, 4.0, 0.02]  # 4m x 4m x 2cm slab

        pose = Pose()
        pose.position.x = 0.0
        pose.position.y = 0.0
        pose.position.z = -0.01   # top surface sits at z=0 (base_link level)
        pose.orientation.w = 1.0

        floor.primitives = [box]
        floor.primitive_poses = [pose]

        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects = [floor]
        self._pub.publish(scene)
        self.get_logger().info('Floor collision plane added to planning scene')
        self._timer.cancel()


def main():
    rclpy.init()
    node = ScenePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
