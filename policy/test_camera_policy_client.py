"""Validate the single-arm contract without cameras, motors, or model weights."""

import unittest

import numpy as np

from camera_policy_client import make_observation, validate_actions


class ContractTests(unittest.TestCase):
    def test_rgb_channels_and_joint_units_are_preserved(self):
        rgb = np.zeros((2, 4, 3), dtype=np.uint8)
        rgb[:, :, 0] = 123
        state = [0.1, -0.2, 0.3, 0.4, 0.5, 0.6, 0.02]
        obs = make_observation(rgb, state, "pick up the block")
        self.assertEqual(obs["images"]["cam_high"].shape, (3, 2, 4))
        self.assertTrue((obs["images"]["cam_high"][0] == 123).all())
        np.testing.assert_allclose(obs["state"], state)

    def test_rejects_bimanual_and_invalid_states(self):
        rgb = np.zeros((2, 4, 3), dtype=np.uint8)
        for state in ([0] * 14, [0] * 6 + [float("nan")]):
            with self.subTest(state=state), self.assertRaises(ValueError):
                make_observation(rgb, state, "test")

    def test_rejects_wrong_action_dimensions_and_nonfinite_values(self):
        for actions in (np.zeros((10, 14)), np.zeros(7), np.zeros((0, 7)),
                        np.full((10, 7), np.inf)):
            with self.subTest(shape=actions.shape), self.assertRaises(ValueError):
                validate_actions({"actions": actions})

    def test_accepts_single_arm_action_chunks(self):
        actions = np.zeros((10, 7), dtype=np.float32)
        actions[:, 6] = 0.02
        np.testing.assert_array_equal(validate_actions({"actions": actions}), actions)


if __name__ == "__main__":
    unittest.main()
