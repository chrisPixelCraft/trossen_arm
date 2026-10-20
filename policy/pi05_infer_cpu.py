"""Run a prediction-only CPU/GPU smoke test of the official PI05 base checkpoint.

Uses synthetic normalized zero state and returns native normalized 32-D base
actions. This is not a fine-tuned WidowX policy and never connects to the arm.
"""

import argparse
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image
from safetensors import safe_open
import torch

from lerobot.configs import NormalizationMode
from lerobot.policies.pi05.configuration_pi05 import PI05Config
from lerobot.policies.pi05.modeling_pi05 import PI05Policy
from lerobot.policies.pi05.processor_pi05 import make_pi05_pre_post_processors


def source_map(keys):
    result = {}
    for key in keys:
        name = key if key.startswith("model.") else "model." + key
        name = name.replace("model.action_time_mlp_in.", "model.time_mlp_in.")
        name = name.replace("model.action_time_mlp_out.", "model.time_mlp_out.")
        result[name] = key
        if name == "model.paligemma_with_expert.paligemma.lm_head.weight":
            result["model.paligemma_with_expert.paligemma.model.language_model.embed_tokens.weight"] = key
    return result


def validate_checkpoint(checkpoint, config):
    original_device = config.device
    config.device = "meta"
    with torch.device("meta"):
        model = PI05Policy(config)
    config.device = original_device
    expected = model.state_dict()
    with safe_open(str(checkpoint / "model.safetensors"), framework="pt", device="cpu") as archive:
        mapping = source_map(archive.keys())
        missing = sorted(set(expected) - set(mapping))
        unexpected = sorted(set(mapping) - set(expected))
        if missing or unexpected:
            raise ValueError(f"權重不相容：missing={missing[:8]}, unexpected={unexpected[:8]}")
        for name, tensor in expected.items():
            actual_shape = archive.get_slice(mapping[name]).get_shape()
            if tuple(actual_shape) != tuple(tensor.shape):
                raise ValueError(f"權重尺寸不相容：{name}: {actual_shape} vs {tuple(tensor.shape)}")
    return mapping


def load_weights(checkpoint, config, mapping):
    from transformers.initialization import no_init_weights

    previous_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.bfloat16)
        # Every persistent tensor is validated and copied from the checkpoint.
        # Skip random initialization; keep regular construction for rotary buffers.
        with no_init_weights():
            model = PI05Policy(config)
    finally:
        torch.set_default_dtype(previous_dtype)
    # Copy one tensor at a time, allowing file-backed FP32 pages to be reclaimed.
    # This avoids keeping an extra full state dict and never silently falls back
    # to randomly initialized parameters if checkpoint loading fails.
    state = model.state_dict()
    with safe_open(str(checkpoint / "model.safetensors"), framework="pt", device="cpu") as archive:
        with torch.no_grad():
            for index, (name, tensor) in enumerate(state.items(), 1):
                tensor.copy_(archive.get_tensor(mapping[name]))
                if index % 160 == 0 or index == len(state):
                    print(f"{config.device} 權重載入：{index}/{len(state)}", flush=True)
    return model.eval()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=Path("checkpoints/pi05_base"))
    parser.add_argument("--image", type=Path, help="RGB snapshot saved by lerobot_observe.py")
    parser.add_argument("--task", default="pick up the block")
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--check-weights-only", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("policy/captures/pi05_cpu_inference"))
    args = parser.parse_args()
    if not args.check_weights_only and args.image is None:
        parser.error("推論需要 --image；或先使用 --check-weights-only。")
    if not args.check_weights_only and not args.image.is_file():
        parser.error(f"找不到影像：{args.image}")
    config = PI05Config.from_pretrained(str(args.checkpoint))
    config.device = args.device
    config.dtype = "bfloat16"
    config.compile_model = False
    config.push_to_hub = False
    config.normalization_mapping = {
        "VISUAL": NormalizationMode.IDENTITY,
        "STATE": NormalizationMode.IDENTITY,
        "ACTION": NormalizationMode.IDENTITY,
    }
    config.validate_features()
    torch.set_num_threads(min(8, os.cpu_count() or 1))
    try:
        if args.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("CUDA 無法使用。")
        mapping = validate_checkpoint(args.checkpoint, config)
        print(f"權重名稱與尺寸檢查通過：{len(mapping)} 個 state tensors。", flush=True)
        if args.check_weights_only:
            return 0
        # Build the tokenizer before allocating the model. A gated-repo failure
        # exits here with instructions instead of wasting time loading weights.
        try:
            preprocess, _ = make_pi05_pre_post_processors(config)
        except OSError as exc:
            raise RuntimeError(
                "無法取得 tokenizer。請到 https://huggingface.co/google/paligemma-3b-pt-224 "
                "取得存取權，並在 trossen_ai_env 執行 hf auth login。"
            ) from exc
        image_key = next(iter(config.image_features))
        with Image.open(args.image) as source:
            rgb = np.asarray(source.convert("RGB")).copy()
        observation = {
            "observation.state": torch.zeros(config.max_state_dim),
            image_key: torch.from_numpy(rgb).permute(2, 0, 1).float() / 255,
            "task": args.task,
        }
        batch = preprocess(observation)
        print("診斷輸入：真實 RGB + 人工 normalized 零狀態；不是 WidowX 狀態。", flush=True)
        print(f"嘗試將模型載入 {args.device}。", flush=True)
        model = load_weights(args.checkpoint, config, mapping)
        start = time.monotonic()
        print(f"開始 {args.device} 推論。", flush=True)
        with torch.inference_mode():
            actions = model.predict_action_chunk(batch).cpu().float().numpy()
        elapsed = time.monotonic() - start
        if not np.isfinite(actions).all():
            raise ValueError("推論結果包含 NaN / infinity。")
        args.output.mkdir(parents=True, exist_ok=True)
        np.save(args.output / "normalized_actions.npy", actions)
        report = {
            "checkpoint": str(args.checkpoint.resolve()),
            "device": args.device, "task": args.task,
            "input_state": "synthetic normalized zeros, not measured robot joints",
            "shape": list(actions.shape), "inference_seconds": elapsed,
            "finite": True, "actions_executed": False,
            "warning": "Native normalized base actions, not WidowX joint targets; no hardware commands.",
        }
        (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)
        print("第一筆 normalized 動作：", actions[0, 0].tolist())
        return 0
    except torch.cuda.OutOfMemoryError as exc:
        report = {
            "checkpoint": str(args.checkpoint.resolve()),
            "device": args.device, "status": "cuda_out_of_memory",
            "inference_completed": False, "actions_executed": False,
            "error": str(exc),
        }
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"GPU 實測顯存不足：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"推論測試停止：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
