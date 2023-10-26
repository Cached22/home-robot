# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.
from typing import Any, Dict, Tuple

from home_robot.utils.config import get_config


class Parameters(object):
    """Wrapper class for handling parameters safely"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getitem__(self, key: str):
        """Just a wrapper to the dictionary"""
        return self.__dict__[key]

    def __str__(self):
        result = ""
        for i, (key, value) in enumerate(self.__dict__.items()):
            if i > 0:
                result += "\n"
            result += f"{key}: {value}"
        return result

    def get_task_goals(parameters) -> Tuple[str, str]:
        """Helper for extracting task information: returns the two different task goals for a very simple OVMM-style (pick, place) task."""
        if "object_to_find" in parameters:
            object_to_find = parameters["object_to_find"]
            if len(object_to_find) == 0:
                object_to_find = None
        else:
            object_to_find = None
        if "location_to_place" in parameters:
            location_to_place = parameters["location_to_place"]
            if len(location_to_place) == 0:
                location_to_place = None
        else:
            location_to_place = None
        return object_to_find, location_to_place

    @staticmethod
    def load(path: str):
        """Load it from the path"""
        return Parameters(**get_config(path)[0])


def get_parameters(path: str):
    """Load parameters from a path"""
    return Parameters.load(path)
