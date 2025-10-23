**Clone repo:**

```console
cd $VTRROOT
git clone git@github.com:utiasASRL/hunter_sim.git
```

**Install dependencies:**

Launch vtr3 docker as root to install Gazebo. We want to specifically use Gazebo Harmonic with ROS2 Humble. To do this, first follow [these instruction](https://gazebosim.org/docs/harmonic/install_ubuntu#binary-installation-on-ubuntu
) to install gz-harmonic from the packages.osrfoundation.org repository.

Afterwards, run the following command to install Gazebo Harmonic:


```console
apt install ros-humble-ros-gzharmonic
```

**Build package:**

In the vtr3 docker run:

```console
source /opt/ros/humble/setup.bash
cd $VTRROOT/hunter_sim
colcon build
```

**Run Hunter LiDAR Sim:**

In the vtr3 docker run:

```console
cd $VTRROOT/hunter_sim
source install/setup.bash
source /opt/ros/humble/setup.bash
ros2 launch hunter2_gazebo hunter_lidar_sim_mars_dome_three.launch.py 
```

This should open Gazebo and spawn in three simulated Hunter 2.0 robots, while exposing relevant topics to ROS2.

**Launch T&R instances:**

In the vtr3 docker run (in another terminal):

```console
cd $VTRROOT/hunter_sim/src/hunter_sim/vtr_hunter
tmuxp load launch/simulated_lidar_hunter.launch.yaml
```

This launches the VT&R instance of the leader. Similar launch files are available for the remaining robots. Launch files to automatically start convoy repeats are also provided.
