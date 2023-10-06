import time

import cv2
import numpy as np
from spot_rl.models import OwlVit
from spot_wrapper.spot import Spot, SpotCamIds
from spot_wrapper.spot import image_response_to_cv2 as imcv2

from home_robot.utils.config import get_config


class GraspController:
    def __init__(
        self,
        config=None,
        spot=None,
        objects=[["ball", "lion"]],
        confidence=0.05,
        show_img=False,
        top_grasp=False,
        hor_grasp=False,
    ):
        self.spot = spot
        self.labels = [f"an image of {y}" for x in objects for y in x]
        self.confidence = confidence
        self.show_img = show_img
        self.top_grasp = top_grasp
        self.hor_grasp = hor_grasp
        self.detector = OwlVit(self.labels, self.confidence, self.show_img)
        self.look = np.deg2rad(config.SPOT.GAZE_ARM_JOINT_ANGLES)
        self.stow = np.deg2rad(config.SPOT.PLACE_ARM_JOINT_ANGLES)
        self.pick_location = []

    def reset_to_look(self):
        """
        Reset the robotic arm to a predefined 'look' position.

        This method sets the joint positions of the
        robotic arm to a predefined 'look' configuration.
        The 'travel_time' parameter controls the speed of
        the movement, and a delay of 1 second is added
        to ensure stability after the movement.

        Args:
            None

        Returns:
            None
        """
        self.spot.set_arm_joint_positions(self.look, travel_time=1.0)
        time.sleep(1)

    def reset_to_stow(self):
        """
        Reset the robotic arm to a predefined 'stow' position.

        This method sets the joint positions of the robotic arm
        to a predefined 'stow' configuration.
        The 'travel_time' parameter controls the speed of the movement,
        and a delay of 1 second is added
        to ensure stability after the movement.

        Args:
            None

        Returns:
            None
        """
        self.spot.set_arm_joint_positions(self.stow, travel_time=1.0)
        time.sleep(1)

    def spot_is_disappointed(self):
        """
        Perform a disappointed arm motion with Spot's arm.

        This method moves Spot's arm back and forth three times to create
        a disappointed motion.

        Returns:
            None
        """
        # Define the angles for disappointed motion
        disappointed_angles = [-np.pi / 8, np.pi / 8]
        self.reset_to_look()
        for _ in range(3):
            for angle in disappointed_angles:
                self.look[3] = angle
                self.spot.set_arm_joint_positions(self.look, travel_time=1)
                time.sleep(1)

        # Reset the arm to its original position
        self.look[3] = 0
        self.spot.set_arm_joint_positions(self.look, travel_time=1)
        time.sleep(0.5)

    def find_obj(self, img) -> np.ndarray:
        """
        Detect and locate an object in an image.

        This method resets the robotic arm to a predefined
        'look' position and then attempts to detect and locate
        an object within the given image. It draws a bounding box and a
        center point on the detected object,
        and optionally displays the annotated image.

        Args:
            img (numpy.ndarray or list): The image in which to detect the
            object. It can be either a numpy.ndarray
                or a list. If it's a list, it will be converted to
                a numpy array.

        Returns:
            np.ndarray: A numpy array representing the center coordinates of the detected object.

        Raises:
            NotImplementedError: If the object cannot be found in the image.
            TypeError: If the input image is not of type numpy.ndarray or list.
        """
        self.reset_to_look()
        if isinstance(img, np.ndarray) or isinstance(img, list):
            if isinstance(img, list):
                img = np.asarray(img)
                print(f" > Converted img from list -> {type(img)}")
            coords = self.detector.run_inference(img)
            if len(coords) > 0:
                print(f" > Result -- {coords}")
                bounding_box = coords[0][2]
                center = np.array(
                    [
                        (bounding_box[0] + bounding_box[2]) / 2,
                        (bounding_box[1] + bounding_box[3]) / 2,
                    ]
                )
                cv2.circle(img, (int(center[0]), int(center[1])), 10, (0, 0, 255), -1)
                cv2.rectangle(
                    img,
                    (bounding_box[0], bounding_box[1]),
                    (bounding_box[2], bounding_box[3]),
                    (0, 255, 0),
                    3,
                )
                if self.show_img:
                    cv2.imshow("img", img)

                filename = f"{coords[0][0].replace(' ', '_')}.jpg"
                cv2.imwrite(filename, img)
                print(f" > Saved {filename}")
                return center
            else:
                return None
        else:
            raise TypeError(f"img is of type {type(img)}, expected is numpy array")

    def sweep(self):
        """
        Perform a sweeping motion while looking for an object.

        This method moves the robot's arm through a series of predefined angles,
        capturing images at each position and searching for an object in the images.

        Returns:
            tuple or None: If an object is found, returns a tuple (x, y) representing
            the pixel coordinates of the object. If no object is found, returns None.
        """
        new_look = self.look
        sweep_angles = [
            -np.pi / 4 + i * np.pi / 8 for i in range(5)
        ]  # Compute sweep angles
        for angle in sweep_angles:
            new_look[0] = angle
            print(f" > Moving to a new position at angle {angle}")
            self.spot.set_arm_joint_positions(new_look, travel_time=1)
            time.sleep(1.0)
            responses = self.spot.get_image_responses([SpotCamIds.HAND_COLOR])
            print(" > Looking for the object")
            pixel = self.find_obj(img=imcv2(responses[0]))
            if pixel is not None:
                print(
                    f" > Object found at {pixel} with spot coords: {self.spot.get_arm_proprioception()}"
                )
                return responses[0], pixel
        return None, None

    def grasp(self, hand_image_response, pixels, timeout=10, count=3):
        """
        Attempt to grasp an object using the robot's hand.

        Parameters:
            - hand_image_response (object): The image response containing the object to grasp.
            - pixels (tuple or None): The pixel coordinates (x, y) of the object in the image.
                                    If set to None, the function will return None.
            - timeout (int, optional): Maximum time (in seconds) to wait for the grasp to succeed.
                                    Defaults to 10 seconds.
            - count (int, optional): Maximum number of grasp attempts before giving up.
                                    Defaults to 3 attempts.

        Returns:
            - success (bool or None): True if the grasp was successful, False if not, None if no pixels provided.

        Note:
            This function attempts to grasp an object located at the specified pixel coordinates in the image.
            It uses the 'spot.grasp_point_in_image' method to perform the grasp operation. If successful, it sets
            the 'pick_location' attribute and then resets the robot's arm to a stow position. The function
            allows for multiple attempts (up to 'count' times) to grasp the object within the specified 'timeout'.
            If 'pixels' is None, the function returns None.

        Example Usage:
            success = robot.grasp(image_response, (320, 240))
            if success:
                print("Grasp successful!")
            else:
                print("Grasp failed.")
        """
        k = 0
        while True:
            if pixels is not None:
                print(f" > Grasping object at {pixels}")
                success = self.spot.grasp_point_in_image(
                    hand_image_response,
                    pixel_xy=pixels,
                    timeout=timeout,
                    top_down_grasp=self.top_grasp,
                    horizontal_grasp=self.hor_grasp,
                )
                if success:
                    print(" > Sucess")
                    self.pick_location = self.spot.get_arm_joint_positions(
                        as_array=True
                    )
                    self.reset_to_stow()
                    time.sleep(1)
                    return success
                k = k + 1
                print(
                    f" > Could not find object from the labels, tries left: {count - k}"
                )
                if k >= count:
                    print(" > Ending trial as target trials reached")
                    return success
            else:
                return None

    def update_label(self, new_label: str):
        """
        Update the labels associated with an image and configure an OwlVit detector.

        This method appends a new label, formatted as "an image of {new_label}",
        to the list of labels.
        It also updates the OwlVit detector with the modified list of labels,
        confidence settings, and
        whether to display images.

        Args:
            new_label (str): Classification of the object to be detected

        Returns:
            None
        """
        self.labels.append(f"an image of {new_label}")
        self.detector = OwlVit(self.labels, self.confidence, self.show_img)

    def get_pick_location(self):
        """
        Get the pick location for an item.

        Returns:
            The pick location as a string.

        This method returns the pick location for the item, which is a string representing
        the location where the item can be picked in a warehouse or similar environment.
        """
        if self.pick_location is not None:
            return self.pick_location
        return None

    def gaze_and_grasp(self):
        image_response = self.spot.get_image_responses([SpotCamIds.HAND_COLOR])
        hand_image_response = image_response[0]
        pixels = self.find_obj(img=imcv2(hand_image_response))
        # print(f" > Finding object at {self.spot.get_arm_proprioception()}")
        if pixels is not None:
            print(f" > Found object at {pixels}, grasping it")
            success = self.grasp(hand_image_response=hand_image_response, pixels=pixels)
            return success
        else:
            print(" > Unable to find the object at initial pose, sweeping through")
            hand_image_response, pixels = self.sweep()
            if pixels is not None:
                print(
                    f" > Object found at {pixels} with spot coords: {self.spot.get_arm_proprioception()}"
                )
                success = self.grasp(
                    hand_image_response=hand_image_response, pixels=pixels
                )
                return success
            else:
                print(" > No object found after sweep...BBBBOOOOOOOOOOOOOOOOO :((")
                self.spot_is_disappointed()

        return None


if __name__ == "__main__":
    CONFIG_PATH = "projects/spot/configs/config.yaml"
    config, config_str = get_config(CONFIG_PATH)
    config.defrost()
    spot = Spot("RealNavEnv")
    gaze = GraspController(
        config=config,
        spot=spot,
        objects=[["penguin plush"]],
        confidence=0.1,
        show_img=True,
        top_grasp=False,
        hor_grasp=True,
    )
    with spot.get_lease(hijack=True):
        spot.power_on()
        spot.blocking_stand()
        time.sleep(1)
        # spot.set_arm_joint_positions(gaze_arm_joint_angles, travel_time=1.0)
        spot.open_gripper()
        time.sleep(1)
        print("Resetting environment...")
        success = gaze.gaze_and_grasp()
        pick = gaze.get_pick_location()
        spot.set_arm_joint_positions(pick, travel_time=1)
        time.sleep(1)
        spot.open_gripper()
        time.sleep(2)
