#!/usr/bin/env python3
import argparse
import configparser
import importlib.machinery
import importlib.util
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--boot-dir", type=Path, required=True)
    parser.add_argument("--adapter")
    parser.add_argument("--storage-dir", type=Path, default=Path("/var/lib/bluetooth"))
    parser.add_argument("--prefix", type=Path, default=Path("/usr/local"))
    parser.add_argument("--init", choices=("systemd", "openrc", "none"))
    parser.add_argument("--destdir", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--enable", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(args.prefix)):
        parser.error("prefix must not contain spaces or shell characters")
    if not args.destdir and not args.boot_dir.is_dir():
        parser.error("boot directory must already be mounted and accessible")
    if not args.destdir and os.geteuid() != 0:
        parser.error("root is required")
    if args.destdir and args.enable:
        parser.error("staging does not support --enable")
    init = args.init
    if init is None:
        init = "systemd" if Path("/run/systemd/system").is_dir() else (
            "openrc" if shutil.which("rc-update") else "none")
    if args.enable and init == "none":
        parser.error("enable requires systemd or OpenRC")

    source = Path(__file__).resolve().parent
    loader = importlib.machinery.SourceFileLoader("bt_sync", str(source / "ps5-bt-sync"))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
    loader.exec_module(module)
    for path in (args.boot_dir, args.storage_dir, args.prefix, args.destdir):
        if path is not None:
            module.check_path(path)
            if any(ord(c) < 32 for c in str(path)):
                parser.error("invalid path")
    if args.adapter:
        adapter = module.address(args.adapter)
    elif args.destdir:
        adapter = None
    else:
        found = module.adapters()
        if len(found) != 1:
            parser.error("select an adapter with --adapter")
        adapter = found[0]

    settings = configparser.ConfigParser(interpolation=None)
    settings["sync"] = dict(boot_directory=str(args.boot_dir),
                            storage_directory=str(args.storage_dir))
    if adapter:
        settings["sync"]["adapter"] = adapter
    output = io.StringIO()
    settings.write(output)
    libexec = args.prefix / "libexec"
    files = [(libexec / "ps5-bt-sync", (source / "ps5-bt-sync").read_bytes(), 0o755),
             (Path("/etc/ps5-bt-sync.conf"), output.getvalue().encode(), 0o600)]
    if init == "systemd":
        unit = (source / "ps5-bt-sync.service").read_text().replace("/usr/local/libexec", str(libexec))
        # Unit paths need quoting and literal percent signs.
        def unit_path(path):
            return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'
        mounts = "[Unit]\nRequiresMountsFor=" + " ".join(
            unit_path(p) for p in (args.boot_dir, args.storage_dir)) + "\n"
        files.extend([(Path("/etc/systemd/system/ps5-bt-sync.service"), unit.encode(), 0o644),
                      (Path("/etc/systemd/system/ps5-bt-sync.service.d/paths.conf"), mounts.encode(), 0o644)])
    elif init == "openrc":
        unit = (source / "ps5-bt-sync.openrc").read_text().replace("/usr/local/libexec", str(libexec))
        files.append((Path("/etc/init.d/ps5-bt-sync"), unit.encode(), 0o755))

    targets = []
    for path, data, mode in files:
        target = args.destdir / path.relative_to("/") if args.destdir else path
        module.check_path(target)
        if target.exists() and not args.replace:
            parser.error("installation exists; review it before using --replace")
        targets.append((target, data, mode))
    pending, installed = [], []
    try:
        for target, data, mode in targets:
            target.parent.mkdir(parents=True, exist_ok=True)
            old = module.read_file(target, 1048576) if target.exists() else None
            old_mode = target.stat().st_mode & 0o777 if old is not None else None
            temporary = module.write_temp(target.parent, data)
            pending.append((target, old, old_mode, temporary))
            os.chmod(temporary, mode)
            if old is not None:
                backup = target.with_name(target.name + f".bak-{time.time_ns()}")
                saved = module.write_temp(target.parent, old)
                try:
                    os.replace(saved, backup)
                finally:
                    saved.unlink(missing_ok=True)
        try:
            for target, old, old_mode, temporary in pending:
                os.replace(temporary, target)
                installed.append((target, old, old_mode))
                module.sync_directory(target.parent)
        except BaseException:
            for target, old, old_mode in reversed(installed):
                if old is None:
                    target.unlink()
                else:
                    temporary = module.write_temp(target.parent, old)
                    os.chmod(temporary, old_mode)
                    os.replace(temporary, target)
                module.sync_directory(target.parent)
            raise
    finally:
        for _, _, _, temporary in pending:
            temporary.unlink(missing_ok=True)
    if args.enable:
        if init == "systemd":
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "enable", "ps5-bt-sync.service"], check=True)
        else:
            subprocess.run(["rc-update", "add", "ps5-bt-sync", "default"], check=True)
    print("pairing sync installed; reboot through the updated PS5 loader")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("installation failed; existing backups retained")
