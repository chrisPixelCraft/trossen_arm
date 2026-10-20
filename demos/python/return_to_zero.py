"""Move a WidowX AI Follower's six arm joints to zero radians.

This is a joint-space move, not encoder homing or a Cartesian origin move.
The gripper receives no position or effort commands. Faults are not cleared.
"""

import argparse
import ipaddress
import math
import sys

import trossen_arm as t


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", default="192.168.1.2")
    parser.add_argument("--duration", type=float, default=8.0,
                        help="Minimum motion duration in seconds (at least 8).")
    parser.add_argument("--check-only", action="store_true",
                        help="Discover the controller and report its error state only.")
    args = parser.parse_args()
    try:
        address = ipaddress.IPv4Address(args.ip)
    except ipaddress.AddressValueError as exc:
        parser.error(str(exc))
    if not math.isfinite(args.duration) or args.duration < 8.0:
        parser.error("--duration must be finite and at least 8 seconds.")

    octets = str(address).split(".")
    host = int(octets[-1])
    if not 1 <= host <= 254:
        parser.error("The controller host octet must be between 1 and 254.")
    results = t.TrossenArmDriver.discover(
        subnet=".".join(octets[:3]), ip_start=host, ip_end=host, timeout=0.1
    )
    if not results:
        print("找不到控制器，未下達移動指令。", file=sys.stderr)
        return 1
    arm = results[0]
    print(f"控制器 {arm.ip}：{t.ERROR_INFORMATION[arm.error_state]}")
    if arm.error_state != t.ErrorState.none:
        print("控制器有故障，停止。請先排除故障；本程式不會清除錯誤。", file=sys.stderr)
        return 1
    if arm.model != t.Model.wxai_v0:
        print("型號不是 wxai_v0，停止。", file=sys.stderr)
        return 1
    if args.check_only:
        return 0

    driver = t.TrossenArmDriver()
    configured = False
    try:
        driver.configure(t.Model.wxai_v0, t.StandardEndEffector.wxai_v0_follower,
                         str(address), False)
        configured = True
        positions = list(driver.get_arm_positions())
        if len(positions) != 6 or not all(math.isfinite(q) for q in positions):
            raise ValueError("無法取得有效的六關節姿勢。")
        limits = driver.get_joint_limits()
        if len(limits) < 6 or any(
            not (limit.position_min <= 0.0 <= limit.position_max)
            for limit in limits[:6]
        ):
            raise ValueError("零角度不在目前關節限制內。")
        print("目前角度（度）：", [round(math.degrees(q), 2) for q in positions])
        print("目標角度（度）：[0, 0, 0, 0, 0, 0]")
        print("這不是直立／收納姿勢，也不是馬達零點校正。")
        print("各關節會同時移動；程式無法偵測桌面或障礙物碰撞。")
        print("確認整段路徑有足夠空間，手離開關節與夾爪。")
        if input("輸入 MOVE 才開始，其餘輸入取消：").strip() != "MOVE":
            print("已取消。")
            return 0

        # Re-read after confirmation because the arm may have been moved.
        positions = list(driver.get_arm_positions())
        if len(positions) != 6 or not all(math.isfinite(q) for q in positions):
            raise ValueError("無法取得有效的六關節姿勢。")
        # Conservative time scaling, not a certified velocity limit.
        duration = max(args.duration, max(abs(q) for q in positions) / 0.1)
        print(f"移動時間：{duration:.1f} 秒。")
        driver.set_arm_modes(t.Mode.position)
        driver.set_arm_positions([0.0] * 6, duration, True)
        driver.set_arm_modes(t.Mode.idle)
        print("移動完成，手臂已切到 idle。")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("操作中止，嘗試切到 idle。", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"失敗：{exc}", file=sys.stderr)
        return 1
    finally:
        if configured:
            try:
                driver.set_arm_modes(t.Mode.idle)
            except Exception as exc:
                print(f"無法確認 idle：{exc}。請支撐手臂。", file=sys.stderr)
            try:
                driver.cleanup()
            except Exception as exc:
                print(f"清理連線失敗：{exc}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
