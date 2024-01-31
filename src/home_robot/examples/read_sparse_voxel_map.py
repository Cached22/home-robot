# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import pickle
from pathlib import Path

import click
import matplotlib.pyplot as plt
import numpy as np

from home_robot.agent.multitask import get_parameters
from home_robot.agent.multitask.robot_agent import RobotAgent
from home_robot.mapping import SparseVoxelMap, SparseVoxelMapNavigationSpace
from home_robot.mapping.voxel import plan_to_frontier
from home_robot.utils.dummy_stretch_client import DummyStretchClient


@click.command()
@click.option(
    "--input-path",
    "-i",
    type=click.Path(),
    default="output.pkl",
    help="Input path with default value 'output.npy'",
)
@click.option(
    "--config-path",
    "-c",
    type=click.Path(),
    default="src/home_robot_hw/configs/default.yaml",
    help="Path to planner config.",
)
@click.option(
    "--frame",
    "-f",
    type=int,
    default=-1,
    help="number of frames to read",
)
@click.option("--show-svm", "-s", type=bool, is_flag=True, default=False)
@click.option("--pkl-is-svm", "-p", type=bool, is_flag=True, default=False)
def main(
    input_path,
    config_path,
    voxel_size: float = 0.01,
    show_maps: bool = True,
    pkl_is_svm: bool = True,
    frame: int = -1,
    show_svm: bool = False,
    try_to_plan_iter: int = 10,
):
    """Simple script to load a voxel map"""
    input_path = Path(input_path)
    print("Loading:", input_path)

    if pkl_is_svm:
        with input_path.open("rb") as f:
            loaded_voxel_map = pickle.load(f)
    else:
        loaded_voxel_map = None

    if len(config_path) > 0:
        print("- Load parameters")
        parameters = get_parameters("src/home_robot_hw/configs/default.yaml")
        print(parameters)
        dummy_robot = DummyStretchClient()
        agent = RobotAgent(
            dummy_robot,
            None,
            parameters,
            rpc_stub=None,
            grasp_client=None,
            voxel_map=loaded_voxel_map,
        )
        voxel_map = agent.voxel_map
        if not pkl_is_svm:
            print("Reading from pkl file of raw observations...")
            voxel_map.read_from_pickle(input_path, num_frames=frame)
    else:
        agent = None
        voxel_map = SparseVoxelMap(resolution=voxel_size)

    if agent is not None:
        print("Agent loaded:", agent)
        # Display with agent overlay
        if show_svm:
            voxel_map.show(instances=True)
        explored, obstacles = voxel_map.get_2d_map(debug=False)
        space = agent.get_navigation_space()
        # TODO: read the parameter from the agent
        frontier, outside, traversible = space.get_frontier()

        plt.subplot(2, 2, 1)
        plt.imshow(explored)
        plt.axis("off")
        plt.title("Explored")

        plt.subplot(2, 2, 2)
        plt.imshow(obstacles)
        plt.axis("off")
        plt.title("Obstacles")

        plt.subplot(2, 2, 3)
        plt.imshow(frontier.cpu().numpy())
        plt.axis("off")
        plt.title("Frontier")

        plt.subplot(2, 2, 4)
        plt.imshow(traversible.cpu().numpy())
        plt.axis("off")
        plt.title("Traversible")

        plt.show()

        print("--- Sampling goals ---")
        # x0 = np.array([0, 0, 0])
        x0 = np.array([-0.17516428, -0.23404302, 5.562937])
        sampler = space.sample_closest_frontier(x0)
        planner = agent.planner

        print(f"Closest frontier to {x0}:")
        start = x0
        for i, g in enumerate(sampler):
            print(i, "sampled", g)
            # Try to plan
            res = plan_to_frontier(
                start,
                planner,
                space,
                voxel_map,
                try_to_plan_iter=try_to_plan_iter,
                visualize=False,
            )
            print("Planning result:", res)


if __name__ == "__main__":
    """run the test script."""
    main()
