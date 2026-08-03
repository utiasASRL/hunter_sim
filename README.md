**Clone repo:**

```console
cd $VTRROOT
git clone https://github.com/utiasasrl/hunter_sim.git
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

**Run Hunter LiDAR Sim:**

In the vtr3 docker run:

```console
cd $VTRROOT/hunter_sim
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch hunter2_gazebo hunter_gazebo_md_sim.launch.py num_robots:=1
```
