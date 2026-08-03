import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float64

class CommandMapperNode(Node):
    def __init__(self):
        super().__init__('command_mapper_node')

        self.wheel_velocity_pub = self.create_publisher(Float64, 'wheel_velocity', 10)
        self.steer_angle_pub = self.create_publisher(Float64, 'steering_angle', 10)
        self.cmd_vel_sub = self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.declare_parameter('wheel_radius', 0.165)

    def cmd_vel_callback(self, msg):
        wheel_velocity = Float64()
        wheel_radius = self.get_parameter('wheel_radius').get_parameter_value().double_value  # meters, adjustable via ROS param
        wheel_velocity.data = msg.linear.x / wheel_radius
        self.wheel_velocity_pub.publish(wheel_velocity)

        steer_angle = Float64()
        steer_angle.data = msg.angular.z
        self.steer_angle_pub.publish(steer_angle)

def main(args=None):
    rclpy.init(args=args)
    node = CommandMapperNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
