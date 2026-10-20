"""Preview D435i + WidowX Follower observations and optionally query OpenPI.

No movement commands are issued. This single-arm observation contract requires
a matching server transform/checkpoint; it is not DROID or bimanual ALOHA.
"""

import argparse
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np
import pyrealsense2 as rs


def make_observation(rgb, state, task):
    state = np.asarray(state, dtype=np.float32)
    if state.shape != (7,) or not np.isfinite(state).all():
        raise ValueError("需要有效的 7 維狀態：6 個關節弧度 + 夾爪位置（公尺）。")
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("相機影像必須是 HWC uint8 RGB。")
    return {
        "state": state,
        "images": {"cam_high": np.ascontiguousarray(rgb.transpose(2, 0, 1))},
        "prompt": task,
    }


def validate_actions(result):
    actions = np.asarray(result["actions"], dtype=np.float32)
    if actions.ndim != 2 or actions.shape[0] == 0 or actions.shape[1] != 7:
        raise ValueError(f"模型動作形狀 {actions.shape} 不符合單臂 [步數, 7]；不可執行。")
    if not np.isfinite(actions).all():
        raise ValueError("模型動作包含 NaN 或 infinity。")
    return actions


def connect_arm(ip):
    import ipaddress
    import trossen_arm as t

    octets = str(ipaddress.IPv4Address(ip)).split(".")
    host = int(octets[-1])
    if not 1 <= host <= 254:
        raise ValueError("控制器 IP 最後一段需為 1–254。")
    found = t.TrossenArmDriver.discover(
        subnet=".".join(octets[:3]), ip_start=host, ip_end=host, timeout=0.1
    )
    if not found:
        raise RuntimeError("找不到手臂控制器。")
    if found[0].error_state != t.ErrorState.none:
        raise RuntimeError(t.ERROR_INFORMATION[found[0].error_state])
    if found[0].model != t.Model.wxai_v0:
        raise RuntimeError("控制器型號不是 wxai_v0。")
    driver = t.TrossenArmDriver()
    driver.configure(t.Model.wxai_v0, t.StandardEndEffector.wxai_v0_follower, ip, False)
    return driver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", default="192.168.1.2")
    parser.add_argument("--serial", default="261222076945")
    parser.add_argument("--camera-only", action="store_true")
    parser.add_argument("--list-cameras", action="store_true", help="List devices without streaming")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--frames", type=int, default=0, help="0: run until Q / Ctrl+C")
    parser.add_argument("--snapshot", type=Path, help="Save last RGB PNG and state JSON here")
    parser.add_argument("--server", help="OpenPI hostname, e.g. 127.0.0.1 (prediction only)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--task", default="")
    args = parser.parse_args()
    if args.frames < 0:
        parser.error("--frames must be nonnegative")
    if args.server and (args.camera_only or not args.task.strip()):
        parser.error("推論需要手臂狀態與 --task；不能搭配 --camera-only。")

    pipeline = rs.pipeline()
    started = False
    driver = None
    socket = None
    rgb = None
    state = None
    try:
        devices = list(rs.context().query_devices())
        for device in devices:
            print("相機：", device.get_info(rs.camera_info.name),
                  device.get_info(rs.camera_info.serial_number))
        if args.list_cameras:
            return 0
        if not any(d.get_info(rs.camera_info.serial_number) == args.serial for d in devices):
            raise RuntimeError(f"找不到相機序號 {args.serial}，請使用 --serial 指定。")
        config = rs.config()
        config.enable_device(args.serial)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.rgb8, 30)
        pipeline.start(config)
        started = True
        if not args.camera_only:
            driver = connect_arm(args.ip)
            print("Follower 已連線，只讀取狀態。請勿同時執行其他手臂程式。")
        if args.server:
            from openpi_client import msgpack_numpy
            from websockets.sync.client import connect

            socket = connect(f"ws://{args.server}:{args.port}", compression=None,
                             max_size=None, open_timeout=5)
            metadata = msgpack_numpy.unpackb(socket.recv(timeout=10))
            print("Policy server metadata:", metadata)
            print("使用單臂 state[7] / images.cam_high[3,H,W] 格式；server 需有對應轉換。")

        print("預覽中：Q 或 Ctrl+C 結束。此程式不會執行模型動作。")
        count = 0
        last_report = 0.0
        last_inference = 0.0
        while args.frames == 0 or count < args.frames:
            frame = pipeline.wait_for_frames(5000).get_color_frame()
            if not frame:
                continue
            rgb = np.asanyarray(frame.get_data()).copy()
            count += 1
            if driver is not None:
                output = driver.get_robot_output()
                state = np.asarray(output.joint.all.positions, dtype=np.float32)
                observation = make_observation(rgb, state, args.task)
            now = time.monotonic()
            if now - last_report >= 1:
                print(f"RGB {rgb.shape}, frame={count}", end="")
                if state is not None:
                    print(" | joints(deg)=", np.round(np.degrees(state[:6]), 1).tolist(),
                          "gripper(m)=", round(float(state[6]), 4))
                else:
                    print()
                last_report = now
            if socket is not None and now - last_inference >= 1:
                socket.send(msgpack_numpy.packb(observation))
                response = socket.recv(timeout=60)
                if isinstance(response, str):
                    raise RuntimeError(response)
                actions = validate_actions(msgpack_numpy.unpackb(response))
                print("預測（未執行）：shape=", actions.shape,
                      "first_action=", actions[0].tolist())
                last_inference = time.monotonic()
            if not args.headless:
                cv2.imshow("D435i - prediction only", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
        if args.snapshot and rgb is not None:
            args.snapshot.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(args.snapshot / "rgb.png"), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
                raise RuntimeError("影像儲存失敗。")
            (args.snapshot / "state.json").write_text(json.dumps({
                "camera_serial": args.serial,
                "arm_ip": None if args.camera_only else args.ip,
                "state": None if state is None else state.tolist(),
                "state_units": ["rad"] * 6 + ["m"],
                "prompt": args.task,
                "note": "Observation snapshot, not a demonstration dataset.",
            }, indent=2), encoding="utf-8")
            print("觀察資料已儲存到", args.snapshot)
        return 0
    except KeyboardInterrupt:
        print("\n已停止。")
        return 130
    except Exception as exc:
        print(f"失敗：{exc}", file=sys.stderr)
        return 1
    finally:
        if socket is not None:
            socket.close()
        if driver is not None:
            try:
                driver.cleanup()
            except Exception as exc:
                print(f"手臂連線清理失敗：{exc}", file=sys.stderr)
        if started:
            pipeline.stop()
        if not args.headless:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    sys.exit(main())
