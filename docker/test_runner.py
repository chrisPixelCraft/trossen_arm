"""Validate Docker command construction without a daemon or hardware."""

import os
from pathlib import Path
import shlex
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


def command(mode, *extra, environment=None):
    result = subprocess.run(
        ["bash", str(ROOT / "docker/run.sh"), "--dry-run", mode, *extra],
        capture_output=True, text=True, check=True,
        env={**os.environ, **(environment or {})},
    )
    return shlex.split(result.stdout)


class RunnerTests(unittest.TestCase):
    def test_build_does_not_fall_through_to_run(self):
        args = command("build")
        self.assertEqual(args[:2], ["docker", "build"])
        self.assertNotIn("run", args)

    def test_gpu_inference_uses_readonly_checkpoint_and_preserves_task(self):
        task = "a task with spaces; $(not-a-command)"
        args = command("infer", "--task", task)
        self.assertIn("--gpus", args)
        self.assertTrue(any("dst=/app/checkpoints,readonly" in arg for arg in args))
        self.assertEqual(args[-2:], ["--task", task])

    def test_cpu_inference_has_no_gpu_requirement(self):
        args = command("infer-cpu")
        self.assertNotIn("--gpus", args)
        self.assertEqual(args[args.index("--device") + 1], "cpu")

    def test_cache_path_with_spaces_and_auth_are_passed_as_arguments(self):
        args = command("auth", environment={"HF_CACHE_DIR": "/tmp/cache with spaces"})
        self.assertIn("type=bind,src=/tmp/cache with spaces,dst=/cache/huggingface", args)
        self.assertEqual(args[-3:], ["hf", "auth", "login"])

    def test_observe_is_the_readonly_entrypoint(self):
        args = command("observe")
        self.assertIn("policy/lerobot_observe.py", args)
        self.assertNotIn("--gpus", args)
        self.assertNotIn("--privileged", args)


if __name__ == "__main__":
    unittest.main()
