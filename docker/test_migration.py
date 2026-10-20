"""Test migration safety/configuration with a fake Docker; no weights or hardware."""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        binary_dir = self.base / "bin"
        binary_dir.mkdir()
        fake = binary_dir / "docker"
        fake.write_text("""#!/usr/bin/env bash
set -eu
case "$1 ${2:-}" in
  'info ') exit 0 ;;
  'image inspect')
    case "$*" in
      *'{{.Size}}'*) printf '%s\\n' 'sha256:test linux/amd64 12' ;;
      *) printf '%s\\n' 'linux/amd64' ;;
    esac ;;
  'image save') printf '%s\\n' 'fake image' > "$4" ;;
  'image load') exit 0 ;;
  *) exit 3 ;;
esac
""")
        fake.chmod(0o755)
        self.env = {**os.environ, "PATH": f"{binary_dir}:{os.environ['PATH']}",
                    "TROSSEN_IMAGE": "trossen-pi05:local"}
        self.bundle = self.base / "bundle with spaces"

    def run_migration(self, *args, check=True):
        return subprocess.run(["bash", str(ROOT / "docker/migrate.sh"), *map(str, args)],
                              env=self.env, text=True, capture_output=True, check=check)

    def export(self):
        self.run_migration("export", self.bundle, "--without-checkpoint")

    def test_export_verify_import_and_portable_layout(self):
        self.export()
        self.run_migration("verify", self.bundle)
        target = self.base / "new project"
        self.run_migration("import", self.bundle, target)
        self.assertTrue((target / "docker/run.sh").is_file())
        self.assertTrue((target / "docker/runtime.env").is_file())
        for excluded in ("checkpoints", "policy/captures", ".git", ".cache"):
            self.assertFalse((target / excluded).exists())
        self.assertNotIn("HF_CACHE_DIR", (target / "docker/runtime.env").read_text())

    def test_corruption_is_rejected_before_import(self):
        self.export()
        (self.bundle / "image.tar").write_text("corrupted")
        target = self.base / "never created"
        self.assertNotEqual(self.run_migration("import", self.bundle, target, check=False).returncode, 0)
        self.assertFalse(target.exists())

    def test_existing_bundle_and_destination_are_not_overwritten(self):
        self.export()
        self.assertNotEqual(self.run_migration("export", self.bundle, "--without-checkpoint", check=False).returncode, 0)
        target = self.base / "existing"
        target.mkdir()
        self.assertNotEqual(self.run_migration("import", self.bundle, target, check=False).returncode, 0)

    def test_configuration_is_data_not_executable_and_env_has_priority(self):
        config = self.base / "settings.env"
        marker = self.base / "must not exist"
        config.write_text(f"ARM_IP=192.168.1.55\nREALSENSE_SERIAL=$(touch {marker})\n")
        code = (f"source {shlex.quote(str(ROOT / 'docker/read_config.sh'))}; "
                f"load_runtime_config {shlex.quote(str(config))}; "
                "printf '%s\\n' \"$ARM_IP\" \"$REALSENSE_SERIAL\"")
        env = {k: v for k, v in os.environ.items() if k not in ("ARM_IP", "REALSENSE_SERIAL")}
        result = subprocess.run(["bash", "-c", code], env={**env, "ARM_IP": "192.168.1.77"},
                                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.splitlines()[0], "192.168.1.77")
        self.assertIn("$(touch", result.stdout)
        self.assertFalse(marker.exists())

    def test_configuration_rejects_unknown_keys(self):
        config = self.base / "bad.env"
        config.write_text("HF_TOKEN=do-not-export-secrets\n")
        code = (f"source {shlex.quote(str(ROOT / 'docker/read_config.sh'))}; "
                f"load_runtime_config {shlex.quote(str(config))}")
        result = subprocess.run(["bash", "-c", code], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("do-not-export-secrets", result.stderr)


if __name__ == "__main__":
    unittest.main()
