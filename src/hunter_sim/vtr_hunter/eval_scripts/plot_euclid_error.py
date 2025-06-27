from argparse import ArgumentParser
from pathlib import Path

from matplotlib import pyplot as plt
import numpy as np
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore

import pandas as pd


def main(file_path):
    # Explicitly create a type store for legacy ROS2 bags without message definitions.
    typestore = get_typestore(Stores.ROS2_GALACTIC)

    leader_list = []
    follower_list = []

    # Create reader instance and open for reading.
    with AnyReader([Path(file_path)], default_typestore=typestore) as reader:
        connections = [x for x in reader.connections if 'odometry' in x.topic ]
        for connection, timestamp, rawdata in reader.messages(connections=connections):
            msg = reader.deserialize(rawdata, connection.msgtype)
            df_list = follower_list if "mr_green" in connection.topic else leader_list
            df_list.append({"t": msg.header.stamp.sec * 1e9 +  msg.header.stamp.nanosec, "x": msg.pose.pose.position.x, "y": msg.pose.pose.position.y, "z": msg.pose.pose.position.z})
    leader = pd.DataFrame(leader_list)
    follower = pd.DataFrame(follower_list)
    print(leader.shape)

    TARGET_OFFSET = 3.5

    error = []
    for row_l in leader.itertuples(index=False):
        row_f = follower.loc[(follower['t']-row_l.t).abs().argsort()[0]].squeeze()
        error.append(np.linalg.norm(row_l[1:3] - row_f[1:3]))

    error = np.array(error)
    print(np.mean(error))
    print(error.shape)
    print(np.sqrt(np.mean(np.power(error - TARGET_OFFSET, 2))))
    plt.plot((leader['t']-leader['t'][0])/1e9, error)
    plt.hlines([TARGET_OFFSET], 0, (leader['t'].max()-leader['t'][0])/1e9, colors=['r'], linestyles=['dashed'])
    plt.grid()
    plt.xlabel("Time (s)")
    plt.ylabel("Distance (m)")
    plt.title("Convoying Distance")
    
    x_leader = np.array(leader['x'])
    y_leader = np.array(leader['y'])
    z_leader = np.array(leader['z'])

    x_follower = np.array(follower['x'])
    y_follower = np.array(follower['y'])
    z_follower = np.array(follower['z'])

    ax3 = plt.figure("Path").add_subplot(projection='3d')
    ax3.plot(x_leader, y_leader, z_leader, label="Leader")
    ax3.plot(x_follower, y_follower, z_follower, label="Follower")
    ax3.legend()
    ax3.set_xlabel("X (m)")
    ax3.set_ylabel("Y (m)")
    ax3.set_zlabel("Z (m)")
    ax3.set_aspect("auto")

    plt.show()

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("rosbag")
    args = parser.parse_args()
    main(args.rosbag)
