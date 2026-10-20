#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$project_root/docker/read_config.sh"
load_runtime_config "$project_root/docker/runtime.env"
image_name="${TROSSEN_IMAGE:-trossen-pi05:local}"
dry_run=false
if [[ "${1:-}" == "--dry-run" ]]; then dry_run=true; shift; fi
mode="${1:-observe}"
if (( $# )); then shift; fi

usage() {
    printf '%s\n' 'Usage: bash docker/run.sh [--dry-run] MODE [extra arguments]' \
        'Modes: build, check, gpu-check, observe, infer, infer-cpu, download, auth' \
        'See docs/docker.md for setup and examples.'
}

print_or_run() {
    if "$dry_run"; then printf '%q ' "$@"; printf '\n'; else exec "$@"; fi
}

case "$mode" in
    help|-h|--help) usage; exit 0 ;;
    build|check|gpu-check|observe|infer|infer-cpu|download|auth) ;;
    *) usage >&2; exit 2 ;;
esac

if ! "$dry_run"; then
    if ! command -v docker >/dev/null; then
        printf '%s\n' 'Docker 尚未安裝。請先看 docs/docker.md 的「安裝」。' >&2
        exit 127
    fi
    if ! docker info >/dev/null 2>&1; then
        printf '%s\n' 'Docker daemon 無法連線：請確認服務已啟動與帳號權限。' >&2
        exit 1
    fi
fi

if [[ "$mode" == build ]]; then
    print_or_run docker build --platform linux/amd64 --tag "$image_name" \
        --file "$project_root/Dockerfile" "$@" "$project_root"
    exit 0
fi

camera_serial="${REALSENSE_SERIAL:-261222076945}"
arm_ip="${ARM_IP:-192.168.1.2}"
captures_dir="$project_root/policy/captures"
checkpoint_dir="$project_root/checkpoints"
hf_cache_dir="${HF_CACHE_DIR:-${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}}"

if ! "$dry_run"; then
    if ! docker image inspect "$image_name" >/dev/null 2>&1; then
        printf '%s\n' 'Image 尚未建置：bash docker/run.sh build' >&2
        exit 1
    fi
    mkdir -p "$captures_dir"
fi

run=(docker run --rm --init --user "$(id -u):$(id -g)" --network host \
    --shm-size 1g --workdir /app \
    --env HF_LEROBOT_HOME=/app/policy/captures/lerobot-cache \
    --mount "type=bind,src=$captures_dir,dst=/app/policy/captures")
if [[ -t 0 && -t 1 ]]; then run+=(-it); fi

case "$mode" in
    infer|infer-cpu|download|auth)
        if ! "$dry_run"; then mkdir -p "$hf_cache_dir"; fi
        run+=(--env HF_HOME=/cache/huggingface \
            --mount "type=bind,src=$hf_cache_dir,dst=/cache/huggingface")
        ;;
esac
case "$mode" in
    infer|infer-cpu|download)
        if [[ "$mode" == download ]]; then
            if ! "$dry_run"; then mkdir -p "$checkpoint_dir"; fi
            run+=(--mount "type=bind,src=$checkpoint_dir,dst=/app/checkpoints")
        else
            if ! "$dry_run" && [[ ! -f "$checkpoint_dir/pi05_base/model.safetensors" ]]; then
                printf '%s\n' '缺少權重：bash docker/run.sh download' >&2
                exit 1
            fi
            run+=(--mount "type=bind,src=$checkpoint_dir,dst=/app/checkpoints,readonly")
        fi
        ;;
esac

case "$mode" in
    gpu-check|infer)
        run+=(--gpus all --env NVIDIA_DRIVER_CAPABILITIES=compute,utility)
        ;;
esac

if [[ "$mode" == observe ]]; then
    # Map only video/USB devices belonging to the selected camera, without privileged mode.
    declare -A groups_added=()
    camera_devices=0
    add_device() {
        local node="$1" group_id
        run+=(--device "$node:$node")
        group_id="$(stat -c '%g' "$node")"
        if [[ -z "${groups_added[$group_id]:-}" ]]; then
            run+=(--group-add "$group_id")
            groups_added[$group_id]=1
        fi
        camera_devices=$((camera_devices + 1))
    }
    for video_dir in /sys/class/video4linux/video*; do
        [[ -d "$video_dir" ]] || continue
        ancestor="$(readlink -f "$video_dir/device")"
        while [[ "$ancestor" != / && -n "$ancestor" ]]; do
            if [[ -f "$ancestor/serial" ]]; then
                serial_value="$(<"$ancestor/serial")"
                if [[ "$serial_value" == "$camera_serial" ]]; then
                    video_node="/dev/$(basename "$video_dir")"
                    [[ ! -e "$video_node" ]] || add_device "$video_node"
                    break
                fi
            fi
            ancestor="$(dirname "$ancestor")"
        done
    done
    for usb_dir in /sys/bus/usb/devices/*; do
        [[ -f "$usb_dir/serial" && -f "$usb_dir/busnum" && -f "$usb_dir/devnum" ]] || continue
        [[ "$(<"$usb_dir/serial")" == "$camera_serial" ]] || continue
        printf -v usb_node '/dev/bus/usb/%03d/%03d' "$(<"$usb_dir/busnum")" "$(<"$usb_dir/devnum")"
        [[ ! -e "$usb_node" ]] || add_device "$usb_node"
    done
    if (( camera_devices == 0 )); then
        if "$dry_run"; then
            printf '%s\n' 'Dry run：相機未連接，略過裝置映射。' >&2
        else
            printf '找不到 RealSense %s；請接上相機或設定 REALSENSE_SERIAL。\n' "$camera_serial" >&2
            exit 1
        fi
    fi
fi

case "$mode" in
    check) command_args=(python docker/verify.py) ;;
    gpu-check) command_args=(python policy/pi05_preflight.py --config-only) ;;
    observe)
        command_args=(python policy/lerobot_observe.py --ip "$arm_ip" --serial "$camera_serial")
        ;;
    infer|infer-cpu)
        inference_device=cuda
        [[ "$mode" != infer-cpu ]] || inference_device=cpu
        command_args=(python policy/pi05_infer.py --device "$inference_device" \
            --image policy/captures/lerobot_check/rgb.png \
            --task 'pick up the blue plush toy' \
            --output "policy/captures/docker_${inference_device}_inference")
        ;;
    download) command_args=(hf download lerobot/pi05_base --local-dir checkpoints/pi05_base) ;;
    auth) command_args=(hf auth login) ;;
esac

print_or_run "${run[@]}" "$image_name" "${command_args[@]}" "$@"
