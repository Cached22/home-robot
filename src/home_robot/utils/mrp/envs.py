import os
import mrp
from mrp import util

import home_robot

PKG_ROOT_DIR = home_robot.__path__[0]
PROJECT_ROOT_DIR = os.path.join(PKG_ROOT_DIR, "../..")

control_pip_deps = ["numpy", "scipy", "sophuspy", f"-e {os.path.abspath(PROJECT_ROOT_DIR)}"]
control_env = mrp.Conda.SharedEnv(
    name="stretch_control_env",
    channels=["conda-forge", "robostack"],
    use_mamba=True,
    dependencies=[
        "python=3.8",
        "cmake",
        "pybind11",
        "ros-noetic-desktop",
        {"pip": control_pip_deps},
    ],
)

catkin_ws_cmd = "source ~/catkin_ws/devel/setup.bash"