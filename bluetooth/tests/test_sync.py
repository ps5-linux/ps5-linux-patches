import importlib.machinery
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader("sync", str(Path(__file__).parents[1] / "ps5-bt-sync"))
sync = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
loader.exec_module(sync)
ADAPTER = "02:00:00:00:00:01"


def bundle():
    return dict(version=2, adapter=ADAPTER, skipped=0, devices=[
        dict(peer="02:00:00:00:00:02", name='Controller "one"',
             type=4, **{"class": 0x2508}, key="12" * 16),
        dict(peer="02:00:00:00:00:03", name="Other accessory",
             type=4, **{"class": 0x2508}, key="34" * 16)])


class SyncTests(unittest.TestCase):
    def test_daemon_check_tolerates_process_exit(self):
        class Process:
            def __init__(self, value):
                self.value = value

            def read_bytes(self):
                if isinstance(self.value, Exception):
                    raise self.value
                return self.value

        with patch.object(Path, "glob", return_value=[Process(ProcessLookupError()), Process(b"\xff")]):
            sync.stopped()
        with patch.object(Path, "glob", return_value=[Process(b"bluetoothd\n")]):
            with self.assertRaises(ValueError):
                sync.stopped()

    def test_schema_rejects_bad_second_entry_before_any_write(self):
        for field, value in (("name", "bad\nKey=value"), ("key", "0" * 32),
                             ("type", True), ("class", 0), ("peer", ADAPTER)):
            data = bundle()
            data["devices"][1][field] = value
            with self.assertRaises(ValueError):
                sync.validate(json.dumps(data), ADAPTER)
        data = bundle()
        data["devices"].append(data["devices"][0])
        with self.assertRaises(ValueError):
            sync.validate(json.dumps(data), ADAPTER)
        with self.assertRaises(ValueError):
            sync.validate(json.dumps(bundle())[:-1] + ',"version":2}', ADAPTER)
        data = bundle()
        data["adapter"] = "02:00:00:00:00:09"
        with self.assertRaises(ValueError):
            sync.validate(json.dumps(data), ADAPTER)

    def test_store_preserves_metadata_and_unrelated_bonds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            device = bundle()["devices"][0]
            target = root / ADAPTER / device["peer"] / "info"
            target.parent.mkdir(parents=True)
            old = b"[General]\nAlias=mine\nSupportedTechnologies=BR/EDR;LE;\n[DeviceID]\nVendor=1356\n"
            target.write_bytes(old)
            other = root / ADAPTER / "02:00:00:00:00:04" / "info"
            other.parent.mkdir()
            other.write_bytes(b"unrelated")
            self.assertEqual(sync.install_bonds(root, ADAPTER, bundle()["devices"]), 2)
            updated = target.read_bytes()
            self.assertIn(b"Alias=mine", updated)
            self.assertIn(b"BR/EDR;LE;", updated)
            self.assertIn(b"Vendor=1356", updated)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            backup = next(target.parent.glob("info.before-ps5-sync-*"))
            self.assertEqual(backup.read_bytes(), old)
            self.assertEqual(sync.install_bonds(root, ADAPTER, bundle()["devices"]), 0)
            self.assertEqual(sync.install_bonds(root, ADAPTER, []), 0)
            self.assertEqual(other.read_bytes(), b"unrelated")

    def test_second_write_failure_rolls_back_first(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / ADAPTER / bundle()["devices"][0]["peer"] / "info"
            target.parent.mkdir(parents=True)
            old = b"[General]\nAlias=original\n"
            target.write_bytes(old)
            replace = sync.os.replace
            writes = 0

            def fail_second(source, destination):
                nonlocal writes
                if Path(destination).name == "info":
                    writes += 1
                    if writes == 2:
                        raise OSError("disk failure")
                return replace(source, destination)

            with patch.object(sync.os, "replace", side_effect=fail_second):
                with self.assertRaises(OSError):
                    sync.install_bonds(root, ADAPTER, bundle()["devices"])
            self.assertEqual(target.read_bytes(), old)
            self.assertFalse((root / ADAPTER / bundle()["devices"][1]["peer"] / "info").exists())
            self.assertFalse(list(root.rglob(".ps5-bt-sync-*")))

    def test_consumption_and_daemon_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config"
            config.write_text(f"[sync]\nadapter={ADAPTER}\nboot_directory={root}\n"
                              f"storage_directory={root / 'store'}\n")
            source = root / "ps5-bt-sync.json"
            data = bundle()
            data["adapter"] = None
            source.write_text(json.dumps(data))
            with patch.object(sync, "adapters", return_value=[ADAPTER]):
                self.assertIn("2 pairings, 2 updated", sync.run(config))
            self.assertFalse(source.exists())
            self.assertEqual(sync.run(config), "no pairing export")
            source.write_text(json.dumps(bundle()))
            with patch.object(sync, "stopped", side_effect=ValueError("active daemon")):
                with self.assertRaises(ValueError):
                    sync.run(config)
            self.assertFalse(source.exists())
            source.write_text("corrupt")
            with patch.object(sync, "adapters", return_value=[ADAPTER]):
                with self.assertRaises(ValueError):
                    sync.run(config)
            self.assertFalse(source.exists())

    def test_adapter_is_optional(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config"
            config.write_text(f"[sync]\nboot_directory={root}\n"
                              f"storage_directory={root / 'store'}\n")
            source = root / "ps5-bt-sync.json"
            data = bundle()
            data["adapter"] = None
            source.write_text(json.dumps(data))
            with patch.object(sync, "adapters", return_value=[ADAPTER]):
                self.assertIn("2 pairings, 2 updated", sync.run(config))
            self.assertTrue((root / "store" / ADAPTER).is_dir())
            self.assertFalse(source.exists())
            source.write_text(json.dumps(data))
            other = "02:00:00:00:00:09"
            with patch.object(sync, "adapters", return_value=[ADAPTER, other]), \
                    patch.object(sync.time, "sleep"):
                with self.assertRaises(ValueError):
                    sync.run(config)
            self.assertFalse(source.exists())
            self.assertFalse((root / "store" / other).exists())

    def test_staging_without_adapter(self):
        path = Path(__file__).parents[1] / "install.py"
        spec = importlib.util.spec_from_file_location("installer", path)
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = [str(path), "--boot-dir", "/efi", "--init", "systemd", "--destdir", str(root)]
            with patch("sys.argv", args):
                installer.main()
            text = (root / "etc/ps5-bt-sync.conf").read_text()
            self.assertIn("boot_directory = /efi", text)
            self.assertNotIn("adapter", text)

    def test_symlinks_and_parent_traversal_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "real").mkdir()
            (root / "link").symlink_to(root / "real", target_is_directory=True)
            with self.assertRaises(ValueError):
                sync.check_path(root / "link" / "info")
            with self.assertRaises(ValueError):
                sync.check_path(root / "real" / ".." / "info")

    def test_kernel_management_adapter_identity(self):
        class ManagementSocket:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def bind(self, address):
                self.bound = address

            def settimeout(self, value):
                pass

            def sendall(self, packet):
                self.command, self.index, length = struct.unpack("<HHH", packet)
                if length:
                    raise AssertionError("unexpected request data")

            def recv(self, size):
                data = struct.pack("<HH", 1, 7) if self.command == 3 else bytes.fromhex("010000000002")
                body = struct.pack("<HB", self.command, 0) + data
                return struct.pack("<HHH", 1, self.index, len(body)) + body

        sock = ManagementSocket()
        with patch.object(sync.socket, "socket", return_value=sock):
            self.assertEqual(sync.adapters(), [ADAPTER])
        self.assertEqual(sock.bound, (0xffff, 3))

    def test_installation_failure_restores_existing_helper(self):
        path = Path(__file__).parents[1] / "install.py"
        spec = importlib.util.spec_from_file_location("installer", path)
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            helper = root / "usr/local/libexec/ps5-bt-sync"
            helper.parent.mkdir(parents=True)
            helper.write_bytes(b"previous helper")
            helper.chmod(0o700)
            replace = installer.os.replace
            failed = False

            def fail_config(source, destination):
                nonlocal failed
                if Path(destination).name == "ps5-bt-sync.conf" and not failed:
                    failed = True
                    raise OSError("disk failure")
                return replace(source, destination)

            args = [str(path), "--boot-dir", "/efi", "--adapter", ADAPTER,
                    "--init", "none", "--destdir", str(root), "--replace"]
            with patch("sys.argv", args), patch.object(installer.os, "replace", side_effect=fail_config):
                with self.assertRaises(OSError):
                    installer.main()
            self.assertEqual(helper.read_bytes(), b"previous helper")
            self.assertEqual(helper.stat().st_mode & 0o777, 0o700)
            self.assertFalse((root / "etc/ps5-bt-sync.conf").exists())
            self.assertFalse((root / "efi/ps5-bt-sync.enabled").exists())
            self.assertFalse(list(root.rglob(".ps5-bt-sync-*")))


if __name__ == "__main__":
    unittest.main()
