"""Check observation-only behavior and the 7-D contract without hardware."""

from types import SimpleNamespace
import unittest

import numpy as np

from lerobot_observe import ObservationOnlyFollower, compact_observation
from pi05_preflight import JOINT_NAMES, single_arm_config


class DriverStub:
    def __init__(self):
        self.configured = False
        self.configure_args = None
        self.cleaned = False

    def get_is_configured(self):
        return self.configured

    def configure(self, *args):
        self.configure_args = args
        self.configured = True

    def cleanup(self):
        self.cleaned = True
        self.configured = False


class CameraStub:
    is_connected = False

    def connect(self):
        self.is_connected = True

    def disconnect(self):
        self.is_connected = False


class LeRobotIntegrationTests(unittest.TestCase):
    def test_connect_and_disconnect_do_not_send_movement_commands(self):
        robot = ObservationOnlyFollower.__new__(ObservationOnlyFollower)
        robot.config = SimpleNamespace(ip_address="192.168.1.2")
        robot.driver = DriverStub()
        robot.cameras = {"image": CameraStub()}
        robot.connect()
        self.assertIs(robot.driver.configure_args[-1], False)
        self.assertTrue(robot.cameras["image"].is_connected)
        with self.assertRaises(RuntimeError):
            robot.send_action({"joint_0.pos": 1.0})
        robot.disconnect()
        self.assertTrue(robot.driver.cleaned)
        self.assertFalse(robot.cameras["image"].is_connected)

    def test_observation_order_and_units_are_preserved(self):
        observation = {f"{name}.pos": i * 0.01 for i, name in enumerate(JOINT_NAMES)}
        observation["image"] = np.zeros((480, 640, 3), dtype=np.uint8)
        compact = compact_observation(observation, JOINT_NAMES)
        np.testing.assert_allclose(compact["observation.state"], np.arange(7) * 0.01)
        observation["joint_0.pos"] = np.nan
        with self.assertRaises(ValueError):
            compact_observation(observation, JOINT_NAMES)

    def test_config_keeps_external_seven_dimensions(self):
        config = single_arm_config()
        self.assertEqual(config.input_features["observation.state"].shape, (7,))
        self.assertEqual(config.output_features["action"].shape, (7,))
        self.assertEqual(config.max_action_dim, 32)
        self.assertEqual(config.action_feature_names[-1], "left_carriage_joint")
        self.assertFalse(config.use_relative_actions)


if __name__ == "__main__":
    unittest.main()
