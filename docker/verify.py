"""Check the packaged environment without connecting hardware or loading weights."""

import json
from importlib.metadata import version
import sys

import numpy
import pyrealsense2
import torch
import trossen_arm
from lerobot_robot_trossen import WidowXAIFollowerConfig


EXPECTED = {"trossen-arm": "1.11.0", "lerobot": "0.6.1", "numpy": "2.2.6"}
for package, expected in EXPECTED.items():
    assert version(package) == expected, (package, version(package))
assert sys.version_info[:2] == (3, 12), sys.version
assert torch.__version__ == "2.7.1+cu126", torch.__version__
assert hasattr(trossen_arm.StandardEndEffector, "wxai_v0_follower")
assert len(WidowXAIFollowerConfig(ip_address="192.168.1.2").joint_names) == 7
print(json.dumps({**EXPECTED, "python": sys.version.split()[0],
                  "torch": torch.__version__, "cuda_available": torch.cuda.is_available()}))
