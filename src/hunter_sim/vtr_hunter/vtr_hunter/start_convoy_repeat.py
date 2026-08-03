import sys
import rclpy
from rclpy.node import Node
from vtr_navigation_msgs.msg import MissionCommand, GoalHandle
import time

repeat_msg = MissionCommand()     
repeat_msg.type = MissionCommand.ADD_GOAL
repeat_msg.goal_handle = GoalHandle()
repeat_msg.goal_handle.type = GoalHandle.REPEAT
repeat_msg.goal_handle.waypoints = [200, 400, 600, 20]
begin_msg = MissionCommand()
begin_msg.type = MissionCommand.BEGIN_GOALS

set_vertex = MissionCommand()
set_vertex.type = MissionCommand.LOCALIZE


select_leader_ctl = MissionCommand()
select_leader_ctl.type = MissionCommand.ADD_GOAL
select_leader_ctl.goal_handle.type = GoalHandle.SELECT_CONTROLLER
select_leader_ctl.goal_handle.controller_name = "bicycle_mpc"

select_follower_ctl = MissionCommand()
select_follower_ctl.type = MissionCommand.ADD_GOAL
select_follower_ctl.goal_handle.type = GoalHandle.SELECT_CONTROLLER
select_follower_ctl.goal_handle.controller_name = "bicycle_mpc_follower"

class ConvoyRepeatNode(Node):
    def __init__(self):
        super().__init__('convoy_repeat_node')

        self.num_robots = self.declare_parameter("num_robots", 1).value
        self.spacing = self.declare_parameter("robot_separation", 2.0).value
        self.edge_len = self.declare_parameter("edge_len", 0.31).value
        self.command_pubs = []

        time.sleep(5.0)

        for i in range(self.num_robots):
            self.command_pubs.append(self.create_publisher(MissionCommand, f'/robot{i}/vtr/mission_command', 10))

        timer_period = 1.0
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.i = 0
        self.leader_messages = [set_vertex, select_leader_ctl, repeat_msg, begin_msg]
        self.follower_messages = [set_vertex, select_follower_ctl, repeat_msg, begin_msg]

    def timer_callback(self):
        if self.i < len(self.leader_messages):
            for rob_id, pub in enumerate(self.command_pubs):

                to_pub = self.leader_messages[self.i] if rob_id == 0 else self.follower_messages[self.i]
                if to_pub.type == MissionCommand.LOCALIZE:
                    to_pub.vertex = int((self.num_robots - rob_id) * self.spacing / self.edge_len)

                pub.publish(to_pub)
            self.get_logger().info(f'Publishing: stage {self.i}')
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
