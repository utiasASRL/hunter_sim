import sys
import rclpy
from rclpy.node import Node
from vtr_navigation_msgs.msg import MissionCommand, GoalHandle

repeat_msg = MissionCommand()     
repeat_msg.type = MissionCommand.ADD_GOAL
repeat_msg.goal_handle = GoalHandle()
repeat_msg.goal_handle.type = GoalHandle.REPEAT
repeat_msg.goal_handle.waypoints = [650]

begin_msg = MissionCommand()
begin_msg.type = MissionCommand.BEGIN_GOALS

class ConvoyRepeatNode(Node):
    def __init__(self):
        super().__init__('convoy_repeat_node')

        super().__init__('minimal_publisher')
        self.command_pub_leader = self.create_publisher(MissionCommand, '/leader/vtr/mission_command', 10)
        self.command_pub_follower = self.create_publisher(MissionCommand, '/follower/vtr/mission_command', 10)
        self.command_pub_follower_2 = self.create_publisher(MissionCommand, '/follower_2/vtr/mission_command', 10) 
        timer_period = 1.0
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.i = 0
        self.messages= [repeat_msg, begin_msg]

    def timer_callback(self):
        if self.i < len(self.messages):
            self.command_pub_leader.publish(self.messages[self.i])
            self.command_pub_follower.publish(self.messages[self.i])
            self.command_pub_follower_2.publish(self.messages[self.i])
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
