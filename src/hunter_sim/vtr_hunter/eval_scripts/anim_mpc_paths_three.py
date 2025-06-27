from argparse import ArgumentParser
from pathlib import Path

from matplotlib import pyplot as plt
import numpy as np
from rosbags.highlevel import AnyReader
from rosbags.typesys import Stores, get_typestore
import matplotlib.animation as anim

from vtr_utils.bag_file_parsing import Rosbag2GraphFactory
from vtr_pose_graph.graph_iterators import PriviledgedIterator
import vtr_pose_graph.graph_utils as g_utils


import pandas as pd


def main(file_path, pose_graph_path):
    # Explicitly create a type store for legacy ROS2 bags without message definitions.
    typestore = get_typestore(Stores.ROS2_GALACTIC)

    leader_list = []
    follower_list = []
    follower_2_list = []

    # Create reader instance and open for reading.
    with AnyReader([Path(file_path)], default_typestore=typestore) as reader:
        connections = [x for x in reader.connections if 'mpc_prediction' in x.topic ]
        for connection, timestamp, rawdata in reader.messages(connections=connections):
            msg = reader.deserialize(rawdata, connection.msgtype)
            if "follower_2" in connection.topic:
                df_list = follower_2_list
            elif "follower" in connection.topic:
                df_list = follower_list
            else:
                df_list = leader_list
            df_list.append({"t": msg.header.stamp.sec * 1e9 +  msg.header.stamp.nanosec, "x": [xi.pose.position.x for xi in msg.poses], "y":  [xi.pose.position.y for xi in msg.poses], "z":  [xi.pose.position.z for xi in msg.poses]})
    leader = pd.DataFrame(leader_list)
    follower = pd.DataFrame(follower_list)
    follower_2 = pd.DataFrame(follower_2_list)
    print(leader.shape)
    print(follower.shape)
    print(follower_2.shape)


    matched_follower = []
    for row_l in leader.itertuples(index=False):
        matched_follower.append(follower.loc[(follower['t']-row_l.t).abs().argsort()[0]].squeeze())
    matched_follower = pd.DataFrame(matched_follower)
    
    matched_follower_2 = []
    for row_l in leader.itertuples(index=False):
        matched_follower_2.append(follower_2.loc[(follower_2['t']-row_l.t).abs().argsort()[0]].squeeze())
    matched_follower_2 = pd.DataFrame(matched_follower_2)
    
    factory = Rosbag2GraphFactory(pose_graph_path)
    graph = factory.buildGraph()
    g_utils.set_world_frame(graph, graph.root)

    # print(f"Graph {graph} has {graph.number_of_vertices} vertices and {graph.number_of_edges} edges")
    x = []
    y = []
    t = []


    # Subtract first time from leader['t'] to get time in seconds
    leader['t'] = leader['t'] - leader.iloc[0]['t']

    for v, e in PriviledgedIterator(graph.root):
        x.append(v.T_v_w.r_ba_ina()[0])
        y.append(v.T_v_w.r_ba_ina()[1])
        t.append(v.stamp)

    fig, ax = plt.subplots(figsize=(4.0, 3.6))
    teach_plot = ax.plot(x, y, label="Teach Path", zorder=1, color="lightblue")[0]
    follow_plot = ax.plot(matched_follower.iloc[0]['x'], matched_follower.iloc[0]['y'], color='limegreen', label="Follower 2", zorder=4)[0]
    follow_circle = ax.scatter(matched_follower.iloc[0]['x'][0], matched_follower.iloc[0]['y'][0], color=follow_plot.get_color(), zorder=5)
    follow_2_plot = ax.plot(matched_follower_2.iloc[0]['x'], matched_follower_2.iloc[0]['y'], color='blue', label="Follower 1", zorder=4)[0]
    follow_2_circle = ax.scatter(matched_follower_2.iloc[0]['x'][0], matched_follower_2.iloc[0]['y'][0], color=follow_2_plot.get_color(), zorder=5)
    lead_plot = ax.plot(leader.iloc[0]['x'], leader.iloc[0]['y'], label="Leader", zorder=2, color="orange")[0]
    lead_circle = ax.scatter(leader.iloc[0]['x'][0], leader.iloc[0]['y'][0], color=lead_plot.get_color(), zorder=3)

    time_text = ax.text(0.02, 0.05, '', transform=ax.transAxes, fontsize=10, verticalalignment='bottom')

    #ax.legend()

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_aspect('equal')




    def update_time_text(i):
        time_text.set_text(f"Time: {leader.iloc[i]['t'] * 1e-9:.2f} s")


    def animate(i):
        update_time_text(i)
        lead_plot.set_xdata(leader.iloc[i]['x'])
        lead_plot.set_ydata(leader.iloc[i]['y'])
        follow_plot.set_xdata(matched_follower.iloc[i]['x'])
        follow_plot.set_ydata(matched_follower.iloc[i]['y'])
        follow_2_plot.set_xdata(matched_follower_2.iloc[i]['x'])
        follow_2_plot.set_ydata(matched_follower_2.iloc[i]['y'])
        lead_circle.set_offsets([leader.iloc[i]['x'][0], leader.iloc[i]['y'][0]])
        follow_circle.set_offsets([matched_follower.iloc[i]['x'][0], matched_follower.iloc[i]['y'][0]])
        follow_2_circle.set_offsets([matched_follower_2.iloc[i]['x'][0], matched_follower_2.iloc[i]['y'][0]])
        x_min = min(min(matched_follower.iloc[i]['x']), min(leader.iloc[i]['x']))
        x_max = max(max(matched_follower.iloc[i]['x']), max(leader.iloc[i]['x']))
        x_av = (x_min + x_max) / 2
        y_min = min(min(matched_follower.iloc[i]['y']), min(leader.iloc[i]['y']))
        y_max = max(max(matched_follower.iloc[i]['y']), max(leader.iloc[i]['y']))
        y_av = (y_min + y_max) / 2
        ax.set_xlim([x_av - 5, x_av + 5])
        ax.set_ylim([y_av - 5, y_av + 5])
 
    #animate scatter plot
    ani = anim.FuncAnimation(fig, animate, 
                            frames = leader.shape[0], interval = 25, repeat = False)
    
    


    ani.save(filename=f"./test_sim.mp4", fps=30, dpi=300, writer="ffmpeg")

    # Compute Euclidean and arclength distances between leader and follower positions

    cumulative_arclength = np.zeros(len(x))
    for i in range(1, len(x)):
        cumulative_arclength[i] = cumulative_arclength[i-1] + np.sqrt((x[i] - x[i-1])**2 + (y[i] - y[i-1])**2)

    distances = []
    arclength_distances = []
    path_offset_leader = []
    path_offset_follower = []
    path_offset_follower_2 = []
    for i in range(len(leader)):
        leader_pos = np.array([[np.array(leader.iloc[i]['x'])[0]], [np.array(leader.iloc[i]['y'])[0]]])
        follower_pos = np.array([[np.array(matched_follower.iloc[i]['x'])[0]], [np.array(matched_follower.iloc[i]['y'])[0]]])
        follower_pos_2 = np.array([[np.array(matched_follower_2.iloc[i]['x'])[0]], [np.array(matched_follower_2.iloc[i]['y'])[0]]])


        # Find the closest points on the teach path for leader and follower
        leader_closest_idx = np.argmin(np.sqrt((x - leader_pos[0])**2 + (y - leader_pos[1])**2))
        follower_closest_idx = np.argmin(np.sqrt((x - follower_pos[0])**2 + (y - follower_pos[1])**2))
        follower_2_closest_idx = np.argmin(np.sqrt((x - follower_pos_2[0])**2 + (y - follower_pos_2[1])**2))


        arclength_distance = 0.0
        # check the indices neighboring the closest one and see which one is closer to follower/leader
        prev_idx = leader_closest_idx - 1
        next_idx = leader_closest_idx + 1
        if prev_idx < 0:
            prev_idx = len(x) - 1
        if next_idx >= len(x):
            next_idx = 0
        if np.linalg.norm(leader_pos - np.array([x[prev_idx], y[prev_idx]])) < np.linalg.norm(leader_pos - np.array([x[next_idx], y[next_idx]])):
            # Project leader position onto the line segment between leader_closest_idx and prev_idx
            v1 = np.array([x[leader_closest_idx], y[leader_closest_idx]]) - np.array([x[prev_idx], y[prev_idx]])
            v2 = leader_pos - np.array([x[prev_idx], y[prev_idx]])
            projection = np.dot(v2.ravel(), v1.ravel()) / np.dot(v1.ravel(), v1.ravel())
            projection = np.clip(projection, 0, 1)  # Ensure projection is within the segment
            projected_point = np.array([x[prev_idx], y[prev_idx]]) + projection * v1
            arclength_distance -= np.linalg.norm(projected_point - np.array([x[leader_closest_idx], y[leader_closest_idx]]))
            # Determine if the leader is to the left or right of the path
            path_vector = np.array([x[leader_closest_idx] - x[prev_idx], y[leader_closest_idx] - y[prev_idx]])
            leader_vector = leader_pos - np.array([x[prev_idx], y[prev_idx]])
            cross_product = np.cross(path_vector.ravel(), leader_vector.ravel())
            if cross_product > 0:
                path_offset_leader.append(np.linalg.norm(projected_point - leader_pos))
            else:
                path_offset_leader.append(-1 * np.linalg.norm(projected_point - leader_pos))
        else:
            # Project leader position onto the line segment between leader_closest_idx and prev_idx
            v1 = np.array([x[leader_closest_idx], y[leader_closest_idx]]) - np.array([x[next_idx], y[next_idx]])
            v2 = leader_pos - np.array([x[next_idx], y[next_idx]])
            projection = np.dot(v2.ravel(), v1.ravel()) / np.dot(v1.ravel(), v1.ravel())
            projection = np.clip(projection, 0, 1)  # Ensure projection is within the segment
            projected_point = np.array([x[next_idx], y[next_idx]]) + projection * v1
            arclength_distance += np.linalg.norm(projected_point - np.array([x[leader_closest_idx], y[leader_closest_idx]]))
            # Determine if the follower is to the left or right of the path
            path_vector = np.array([x[leader_closest_idx] - x[next_idx], y[leader_closest_idx] - y[next_idx]])
            leader_vector = leader_pos - np.array([x[next_idx], y[next_idx]])
            cross_product = np.cross(path_vector.ravel(), leader_vector.ravel())
            if cross_product > 0:
                path_offset_leader.append(-1 * np.linalg.norm(projected_point - leader_pos))
            else:
                path_offset_leader.append(np.linalg.norm(projected_point - leader_pos))

        prev_idx = follower_closest_idx - 1
        next_idx = follower_closest_idx + 1
        if prev_idx < 0:
            prev_idx = len(x) - 1
        if next_idx >= len(x):
            next_idx = 0
        if np.linalg.norm(follower_pos - np.array([x[prev_idx], y[prev_idx]])) < np.linalg.norm(follower_pos - np.array([x[next_idx], y[next_idx]])):
            # Project follower position onto the line segment between follower_closest_idx and prev_idx
            v1 = np.array([x[follower_closest_idx], y[follower_closest_idx]]) - np.array([x[prev_idx], y[prev_idx]])
            v2 = follower_pos - np.array([x[prev_idx], y[prev_idx]])
            projection = np.dot(v2.ravel(), v1.ravel()) / np.dot(v1.ravel(), v1.ravel())
            projection = np.clip(projection, 0, 1)  # Ensure projection is within the segment
            projected_point = np.array([x[prev_idx], y[prev_idx]]) + projection * v1
            arclength_distance += np.linalg.norm(projected_point - np.array([x[follower_closest_idx], y[follower_closest_idx]]))

            # Determine if the leader is to the left or right of the path
            path_vector = np.array([x[follower_closest_idx] - x[prev_idx], y[follower_closest_idx] - y[prev_idx]])
            follower_vector = follower_pos - np.array([x[prev_idx], y[prev_idx]])
            cross_product = np.cross(path_vector.ravel(), follower_vector.ravel())
            if cross_product > 0:
                path_offset_follower.append(np.linalg.norm(projected_point - follower_pos))
            else:
                path_offset_follower.append(-1 * np.linalg.norm(projected_point - follower_pos))
        else:
            # Project follower position onto the line segment between follower_closest_idx and next_idx
            v1 = np.array([x[follower_closest_idx], y[follower_closest_idx]]) - np.array([x[next_idx], y[next_idx]])
            v2 = follower_pos - np.array([x[next_idx], y[next_idx]])
            projection = np.dot(v2.ravel(), v1.ravel()) / np.dot(v1.ravel(), v1.ravel())
            projection = np.clip(projection, 0, 1)  # Ensure projection is within the segment
            projected_point = np.array([x[next_idx], y[next_idx]]) + projection * v1
            arclength_distance -= np.linalg.norm(projected_point - np.array([x[follower_closest_idx], y[follower_closest_idx]]))

            # Determine if the follower is to the left or right of the path
            path_vector = np.array([x[follower_closest_idx] - x[next_idx], y[follower_closest_idx] - y[next_idx]])
            follower_vector = follower_pos - np.array([x[next_idx], y[next_idx]])
            cross_product = np.cross(path_vector.ravel(), follower_vector.ravel())
            if cross_product > 0:
                path_offset_follower.append(-1 * np.linalg.norm(projected_point - follower_pos))
            else:
                path_offset_follower.append(np.linalg.norm(projected_point - follower_pos))
                
        prev_idx = follower_2_closest_idx - 1
        next_idx = follower_2_closest_idx + 1
        if prev_idx < 0:
            prev_idx = len(x) - 1
        if next_idx >= len(x):
            next_idx = 0
        if np.linalg.norm(follower_pos_2 - np.array([x[prev_idx], y[prev_idx]])) < np.linalg.norm(follower_pos_2 - np.array([x[next_idx], y[next_idx]])):
            # Project follower position onto the line segment between follower_closest_idx and prev_idx
            v1 = np.array([x[follower_2_closest_idx], y[follower_2_closest_idx]]) - np.array([x[prev_idx], y[prev_idx]])
            v2 = follower_pos_2 - np.array([x[prev_idx], y[prev_idx]])
            projection = np.dot(v2.ravel(), v1.ravel()) / np.dot(v1.ravel(), v1.ravel())
            projection = np.clip(projection, 0, 1)  # Ensure projection is within the segment
            projected_point = np.array([x[prev_idx], y[prev_idx]]) + projection * v1
           
            # Determine if the leader is to the left or right of the path
            path_vector = np.array([x[follower_2_closest_idx] - x[prev_idx], y[follower_2_closest_idx] - y[prev_idx]])
            follower_2_vector = follower_pos_2 - np.array([x[prev_idx], y[prev_idx]])
            cross_product = np.cross(path_vector.ravel(), follower_2_vector.ravel())
            if cross_product > 0:
                path_offset_follower_2.append(np.linalg.norm(projected_point - follower_pos_2))
            else:
                path_offset_follower_2.append(-1 * np.linalg.norm(projected_point - follower_pos_2))
        else:
            # Project follower position onto the line segment between follower_closest_idx and next_idx
            v1 = np.array([x[follower_2_closest_idx], y[follower_2_closest_idx]]) - np.array([x[next_idx], y[next_idx]])
            v2 = follower_pos_2 - np.array([x[next_idx], y[next_idx]])
            projection = np.dot(v2.ravel(), v1.ravel()) / np.dot(v1.ravel(), v1.ravel())
            projection = np.clip(projection, 0, 1)  # Ensure projection is within the segment
            projected_point = np.array([x[next_idx], y[next_idx]]) + projection * v1
           
            # Determine if the follower is to the left or right of the path
            path_vector = np.array([x[follower_2_closest_idx] - x[next_idx], y[follower_2_closest_idx] - y[next_idx]])
            follower_2_vector = follower_pos_2 - np.array([x[next_idx], y[next_idx]])
            cross_product = np.cross(path_vector.ravel(), follower_2_vector.ravel())
            if cross_product > 0:
                path_offset_follower_2.append(-1 * np.linalg.norm(projected_point - follower_pos_2))
            else:
                path_offset_follower_2.append(np.linalg.norm(projected_point - follower_pos_2))

        # Compute arclength distance using cumulative arclength
        arclength_distance += abs(cumulative_arclength[leader_closest_idx] - cumulative_arclength[follower_closest_idx])
        distances.append(np.linalg.norm(leader_pos - follower_pos))
        arclength_distances.append(arclength_distance)



    # Skip first X seconds and discard data accordingly
    start_time = 3.0
    mask = leader['t'] >= start_time * 1e9
    leader = leader[mask]
    distances = [distances[i] for i in range(len(distances)) if mask.iloc[i]]
    arclength_distances = [arclength_distances[i] for i in range(len(arclength_distances)) if mask.iloc[i]]
    path_offset_leader = [path_offset_leader[i] for i in range(len(path_offset_leader)) if mask.iloc[i]]
    path_offset_follower = [path_offset_follower[i] for i in range(len(path_offset_follower)) if mask.iloc[i]]
    path_offset_follower_2 = [path_offset_follower_2[i] for i in range(len(path_offset_follower_2)) if mask.iloc[i]]


    # Create a new figure for the combined distance plot
    fig_combined, ax_combined = plt.subplots(figsize=(6, 4))
    ax_combined.plot(leader['t'].to_numpy() * 1e-9, distances, label="Euclidean Distance", color="blue")
    ax_combined.plot(leader['t'].to_numpy() * 1e-9, arclength_distances, label="Arclength Distance", color="green")
    ax_combined.axhline(y=3, color='red', linestyle='--', label="Desired")
    ax_combined.set_xlabel("Time (s)")
    ax_combined.set_ylabel("Distance (m)")
    ax_combined.set_title("Leader-Follower Distances Over Time")
    ax_combined.legend(loc='upper left', bbox_to_anchor=(1, 1))
    fig_combined.tight_layout()  # Ensure everything fits within the figure boundaries

    # Save the combined distance plot as a separate file
    fig_combined.savefig("./combined_distance_plot.png", dpi=300)

    # Create a new figure for the path offset plot
    fig_offset, ax_offset = plt.subplots(figsize=(6, 4))
    ax_offset.plot(leader['t'].to_numpy() * 1e-9, path_offset_leader, label="Leader Path Offset", color="orange")
    ax_offset.plot(leader['t'].to_numpy() * 1e-9, path_offset_follower, label="Follower 2 Path Offset", color="limegreen")
    ax_offset.plot(leader['t'].to_numpy() * 1e-9, path_offset_follower_2, label="Follower Path Offset", color="blue")
    ax_offset.set_xlabel("Time (s)")
    ax_offset.set_ylabel("Path Offset (m)")
    ax_offset.set_title("Path Offset Over Time")
    ax_offset.legend(loc='upper left', bbox_to_anchor=(1, 1))
    fig_offset.tight_layout()  # Ensure everything fits within the figure boundaries

    # Save the path offset plot as a separate file
    fig_offset.savefig("./path_offset_plot.png", dpi=300)




if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("rosbag")
    parser.add_argument("pose_graph")
    args = parser.parse_args()
    main(args.rosbag, args.pose_graph)
