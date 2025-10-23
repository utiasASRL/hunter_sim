import sys
import rclpy
from rclpy.node import Node
from vtr_navigation_msgs.msg import MissionCommand, GoalHandle
import time

repeat_msg = MissionCommand()     
repeat_msg.type = MissionCommand.ADD_GOAL
repeat_msg.goal_handle = GoalHandle()
repeat_msg.goal_handle.type = GoalHandle.REPEAT
repeat_msg.goal_handle.waypoints = [650]

begin_msg = MissionCommand()
begin_msg.type = MissionCommand.BEGIN_GOALS

set_vertex_4 = MissionCommand()
set_vertex_4.type = MissionCommand.LOCALIZE
set_vertex_4.vertex = 8

set_vertex_5 = MissionCommand()
set_vertex_5.type = MissionCommand.LOCALIZE
set_vertex_5.vertex = 4

set_vertex_6 = MissionCommand()
set_vertex_6.type = MissionCommand.LOCALIZE
set_vertex_6.vertex = 0


class ConvoyRepeatNode(Node):
    def __init__(self):
        super().__init__('convoy_repeat_node')

        super().__init__('minimal_publisher')
        self.command_pub_follower_3 = self.create_publisher(MissionCommand, '/follower_3/vtr/mission_command', 10)
        self.command_pub_follower_4 = self.create_publisher(MissionCommand, '/follower_4/vtr/mission_command', 10)
        self.command_pub_follower_5 = self.create_publisher(MissionCommand, '/follower_5/vtr/mission_command', 10) 
        timer_period = 1.0
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.i = 0
        self.messages_4 = [set_vertex_4, repeat_msg, begin_msg]
        self.messages_5 = [set_vertex_5, repeat_msg, begin_msg]
        self.messages_6 = [set_vertex_6, repeat_msg, begin_msg]

    def timer_callback(self):
        if self.i < len(self.messages_4):
            self.command_pub_follower_5.publish(self.messages_6[self.i])
            time.sleep(2)
            self.command_pub_follower_4.publish(self.messages_5[self.i])
            time.sleep(2)
            self.command_pub_follower_3.publish(self.messages_4[self.i])
            self.get_logger().info('Publishing:')
            self.i += 1
        else:
            sys.exit(0)

def main(args=None):
    rclpy.init(args=args)
    node = ConvoyRepeatNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
