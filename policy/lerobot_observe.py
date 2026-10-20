"""Read D435i + WidowX through LeRobot, without staged moves or actions."""

import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
import trossen_arm as t
from lerobot.cameras.realsense.configuration_realsense import RealSenseCameraConfig
from lerobot_robot_trossen import WidowXAIFollower, WidowXAIFollowerConfig


class ObservationOnlyFollower(WidowXAIFollower):
    """Use official feature/read interfaces; never issue position commands."""

    def connect(self, calibrate=False):
        if self.driver.get_is_configured():
            raise RuntimeError("手臂已連線。")
        self.driver.configure(t.Model.wxai_v0, t.StandardEndEffector.wxai_v0_follower,
                              self.config.ip_address, False)
        for camera in self.cameras.values():
            camera.connect()

    def configure(self):
        pass

    def send_action(self, action):
        raise RuntimeError("觀察模式禁止下達動作。")

    def disconnect(self):
        errors = []
        for camera in self.cameras.values():
            if camera.is_connected:
                try:
                    camera.disconnect()
                except Exception as exc:
                    errors.append(str(exc))
        if self.driver.get_is_configured():
            try:
                self.driver.cleanup()
            except Exception as exc:
                errors.append(str(exc))
        if errors:
            raise RuntimeError("; ".join(errors))


def compact_observation(observation, joint_names):
    state = np.asarray([observation[f"{name}.pos"] for name in joint_names], dtype=np.float32)
    if state.shape != (7,) or not np.isfinite(state).all():
        raise ValueError("需要有效的 7 維關節／夾爪狀態。")
    image = observation["image"]
    if image is None or image.dtype != np.uint8 or image.ndim != 3 or image.shape[-1] != 3:
        raise ValueError("尚未取得有效的 RGB 影像。")
    return {"observation.state": state, "observation.images.image": image}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", default="192.168.1.2")
    parser.add_argument("--serial", default="261222076945")
    parser.add_argument("--frames", type=int, default=60)
    parser.add_argument("--output", type=Path, default=Path("policy/captures/lerobot_check"))
    args = parser.parse_args()
    if args.frames < 1:
        parser.error("--frames must be at least 1")
    config = WidowXAIFollowerConfig(
        ip_address=args.ip, id="widowx_follower",
        cameras={"image": RealSenseCameraConfig(
            serial_number_or_name=args.serial, width=640, height=480, fps=30,
        )},
    )
    robot = ObservationOnlyFollower(config)
    try:
        robot.connect()
        print("LeRobot 已連線；只讀觀察，不執行動作。")
        compact = None
        deadline = time.monotonic() + 10
        while compact is None:
            try:
                compact = compact_observation(robot.get_observation(), config.joint_names)
            except ValueError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.05)
        for index in range(args.frames):
            compact = compact_observation(robot.get_observation(), config.joint_names)
            if index % 30 == 0:
                print("state:", compact["observation.state"].tolist(),
                      "RGB:", compact["observation.images.image"].shape)
            time.sleep(1 / 30)
        from PIL import Image

        args.output.mkdir(parents=True, exist_ok=True)
        Image.fromarray(compact["observation.images.image"]).save(args.output / "rgb.png")
        (args.output / "observation.json").write_text(json.dumps({
            "observation.state": compact["observation.state"].tolist(),
            "joint_names": config.joint_names,
            "units": ["rad"] * 6 + ["m"],
            "camera_serial": args.serial,
            "image_path": "rgb.png",
            "note": "Observation only; not demonstration actions or training data.",
        }, indent=2), encoding="utf-8")
        print("觀察快照：", args.output)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"觀察測試失敗：{exc}", file=sys.stderr)
        return 1
    finally:
        try:
            robot.disconnect()
        except Exception as exc:
            print(f"清理失敗：{exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
