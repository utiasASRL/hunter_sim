**Clone repo:**

```console
cd $VTRROOT
git clone https://github.com/utiasasrl/hunter_sim.git
cd hunter_sim
```

**Build Dockerfile**
This is based on the latest GPU vtr3 Dockerfile on Dockerhub
```bash
docker build -t utiasasrl/vtr3-gazebo:latest .
```

**Run Docker Container**
```bash
docker run -it --name hunter_sim   --privileged   --network=host   --ipc=host   --gpus=all   -e USER_ID=$(id -u)   -e GROUP_ID=$(id -g)   -e USER_NAME=$(id -un)   -e DISPLAY=$DISPLAY   -v /tmp/.X11-unix:/tmp/.X11-unix:rw   -v ${VTRROOT}:${VTRROOT}:rw   -v /dev:/dev -e NVIDIA_DRIVER_CAPABILITIES=all  utiasasrl/vtr3-gazebo:latest
```

**Build package:**

In the docker run:

```console
source /opt/ros/humble/setup.bash
cd $VTRROOT/hunter_sim
colcon build
```

**Run Hunter Sim For One Robot:**

In the gazebo docker run:

```bash
cd $VTRROOT/hunter_sim
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch hunter2_gazebo hunter_gazebo_md_sim.launch.py num_robots:=1
```
After the simulation has begun, and stabilized, in a second terminal launch vtr.

```bash
tmuxp load $VTRROOT/src/hunter_sim/vtr_hunter/launch/simulated_lidar_hunter.launch.yaml
```
You can navigate to http://localhost:5200 and interact with the GUI same as if it were a real robot. 
To manually drive the robot to teach use the default ros teleop nodes. 

For a keyboard only
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r __ns:=/robot0
```

If you have access to a gamepad
```bash
ros2 run teleop_twist_joy teleop_node --ros-args -r __ns:=/robot0
```

**Run Hunter Sim For a Convoy:**

In the Gazebo Docker run:

```bash
cd $VTRROOT/hunter_sim
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch hunter2_gazebo hunter_gazebo_md_sim.launch.py num_robots:=3 robot_spacing:=2.0
```

After the simulation has begun, and stabilized, in a second terminal launch vtr.

```bash
tmuxp load $VTRROOT/src/hunter_sim/vtr_hunter/launch/simulated_lidar_convoy_three.launch.yaml
```

The tmux file is very small now, you can run the convoy easily with any reasonable number of robots.
