"""Validate a 7-D LeRobot PI05 config and estimate memory without loading weights."""

import argparse
from collections import Counter
import json
from pathlib import Path

import torch
from lerobot.configs import FeatureType, PolicyFeature
from lerobot.policies.pi05.configuration_pi05 import PI05Config


JOINT_NAMES = [f"joint_{index}" for index in range(6)] + ["left_carriage_joint"]


def single_arm_config():
    config = PI05Config(
        device="cpu", dtype="bfloat16", compile_model=False,
        input_features={
            "observation.state": PolicyFeature(type=FeatureType.STATE, shape=(7,)),
            "observation.images.image": PolicyFeature(type=FeatureType.VISUAL, shape=(3, 480, 640)),
        },
        output_features={"action": PolicyFeature(type=FeatureType.ACTION, shape=(7,))},
        action_feature_names=JOINT_NAMES,
        use_relative_actions=False,
        freeze_vision_encoder=True,
        train_expert_only=True,
        gradient_checkpointing=True,
    )
    config.validate_features()
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("policy/captures/pi05_preflight"))
    parser.add_argument("--config-only", action="store_true")
    args = parser.parse_args()
    config = single_arm_config()
    args.output.mkdir(parents=True, exist_ok=True)
    config.save_pretrained(args.output)
    report = {
        "state_dim": 7, "action_dim": 7, "joint_names": JOINT_NAMES,
        "state_units": ["rad"] * 6 + ["m"],
        "internal_state_dim": config.max_state_dim,
        "internal_action_dim": config.max_action_dim,
        "cuda_available": torch.cuda.is_available(),
        "weights_loaded": False,
        "note": "Configuration and memory check only. No trained policy or inference.",
    }
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        report.update(gpu=torch.cuda.get_device_name(), gpu_free_gib=free / 2**30,
                      gpu_total_gib=total / 2**30)
        # Test the GPU backend using tiny tensors, not a robot policy.
        x = torch.ones((128, 128), device="cuda", dtype=torch.bfloat16)
        assert torch.isfinite(x @ x).all()
        del x
        torch.cuda.empty_cache()
        report["cuda_bfloat16_smoke_test"] = "passed"
    if not args.config_only:
        from lerobot.policies.pi05.modeling_pi05 import PI05Policy

        # Meta tensors carry shapes and dtypes only; no model weights are allocated.
        config.device = "meta"
        with torch.device("meta"):
            model = PI05Policy(config)
        dtype_bytes = Counter()
        trainable_bytes = 0
        for parameter in model.parameters():
            size = parameter.numel() * parameter.element_size()
            dtype_bytes[str(parameter.dtype)] += size
            if parameter.requires_grad:
                trainable_bytes += size
        model_bytes = sum(dtype_bytes.values())
        report.update(
            parameter_count=sum(p.numel() for p in model.parameters()),
            parameter_gib=model_bytes / 2**30,
            parameter_bytes_by_dtype=dict(dtype_bytes),
            trainable_parameter_gib=trainable_bytes / 2**30,
        )
        if report["cuda_available"]:
            report["free_gib_after_parameters_estimate"] = report["gpu_free_gib"] - model_bytes / 2**30
        report["memory_note"] = (
            "Parameters only: activations, cache, gradients, optimizer and allocator overhead are extra. "
            "This estimate does not prove the model can run or train on this GPU."
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
