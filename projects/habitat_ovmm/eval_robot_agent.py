# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.


import argparse
import logging
import os

from home_robot.agent.multitask import get_parameters
from home_robot.agent.multitask.robot_agent import RobotAgent
from home_robot.perception import create_semantic_sensor
from loguru import logger
from ovmm_sim_client import OvmmSimClient, SimGraspPlanner

from utils.config_utils import (
    create_agent_config,
    create_env_config,
    get_habitat_config,
    get_omega_config,
)
from utils.env_utils import create_ovmm_env_fn

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_episodes", type=int, default=None)
    parser.add_argument(
        "--habitat_config_path",
        type=str,
        default="ovmm/ovmm_eval.yaml",
        help="Path to config yaml",
    )
    parser.add_argument(
        "--baseline_config_path",
        type=str,
        default="projects/habitat_ovmm/configs/agent/heuristic_agent.yaml",
        help="Path to config yaml",
    )
    parser.add_argument(
        "--env_config_path",
        type=str,
        default="projects/habitat_ovmm/configs/env/hssd_eval.yaml",
        help="Path to config yaml",
    )
    parser.add_argument(
        "--device_id",
        type=int,
        default=0,
        help="GPU device id",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=5,
        help="rate?",
    )
    parser.add_argument(
        "--manual_wait",
        type=bool,
        default=False,
        help="manual_wait?",
    )
    parser.add_argument(
        "--navigate_home",
        type=bool,
        default=False,
        help="manual_wait?",
    )
    parser.add_argument(
        "--verbose",
        type=bool,
        default=True,
        help="verbose output",
    )
    parser.add_argument(
        "--show_intermediate_maps",
        type=bool,
        default=True,
        help="verbose output",
    )

    parser.add_argument(
        "overrides",
        default=None,
        nargs=argparse.REMAINDER,
        help="Modify config options from command line",
    )

    args = parser.parse_args()

    # get habitat config
    habitat_config, _ = get_habitat_config(
        args.habitat_config_path, overrides=args.overrides
    )

    # get baseline config
    baseline_config = get_omega_config(args.baseline_config_path)

    # get env config
    env_config = get_omega_config(args.env_config_path)

    # merge habitat and env config to create env config
    env_config = create_env_config(habitat_config, env_config, evaluation_type="local")

    logger.info("Creating OVMM simulation environment")
    env = create_ovmm_env_fn(env_config)

    robot = OvmmSimClient(sim_env=env, is_stretch_robot=True)

    print("- Create semantic sensor based on detic")
    config, semantic_sensor = create_semantic_sensor(
        device_id=args.device_id, verbose=args.verbose
    )

    grasp_client = SimGraspPlanner(robot)

    parameters = get_parameters("src/home_robot_hw/configs/default.yaml")
    print(parameters)
    object_to_find, location_to_place = parameters.get_task_goals()

    stub = None

    demo = RobotAgent(
        robot, semantic_sensor, parameters, rpc_stub=stub, grasp_client=grasp_client
    )
    demo.start(goal=object_to_find, visualize_map_at_start=args.show_intermediate_maps)

    matches = demo.get_found_instances_by_class(object_to_find)

    print(matches)

    demo.run_exploration(
        args.rate,
        args.manual_wait,
        explore_iter=parameters["exploration_steps"],
        task_goal=object_to_find,
        go_home_at_end=args.navigate_home,
    )

    matches = demo.get_found_instances_by_class(object_to_find)
    breakpoint()

    # merge env config and baseline config to create agent config
    agent_config = create_agent_config(env_config, baseline_config)

    device_id = env_config.habitat.simulator.habitat_sim_v0.gpu_device_id

    # create agent
    if args.agent_type == "random":
        agent = RandomAgent(agent_config, device_id=device_id)
    else:
        agent = OpenVocabManipAgent(agent_config, device_id=device_id)

    # create evaluator
    evaluator = OVMMEvaluator(env_config)

    # evaluate agent
    metrics = evaluator.evaluate(
        agent=agent,
        evaluation_type=args.evaluation_type,
        num_episodes=args.num_episodes,
    )
    print("Metrics:\n", metrics)
