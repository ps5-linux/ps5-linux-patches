# PS5 Bluetooth pairing sync

Imports active classic Bluetooth pairings from PS5 OS into BlueZ. Pair devices
in PS5 OS, then boot through a loader with pairing export support. Linux-only
bonds are kept. Removing a PS5 OS pairing does not remove its Linux bond.

Requires Linux, BlueZ and Python 3.8 or newer. No Python packages or BlueZ command
line tools are needed. The importer is independent of the init system; systemd
and OpenRC startup files are included.

## Install

Use the directory containing the initrd selected by the loader, on the mounted
boot partition. For the usual layout:

```sh
sudo python3 bluetooth/install.py --boot-dir /boot/efi --enable
```

The installer selects the adapter if exactly one is present. With multiple
adapters, pass `--adapter AA:BB:CC:DD:EE:FF` for the console's internal adapter.
Use `--storage-dir` if BlueZ uses a directory other than `/var/lib/bluetooth`.
`--prefix` changes the helper's installation prefix, normally `/usr/local`.
Existing installation files require `--replace`, which saves backups first.

The installer writes `/etc/ps5-bt-sync.conf`. The updated loader exports all usable
active classic bonds by default, without a marker or device whitelist.

Init detection can be overridden with `--init systemd`, `--init openrc` or
`--init none`. With systemd, the importer is ordered before `bluetooth.service`
and after the configured filesystems. With OpenRC, it needs `localmount` and runs
before `bluetooth`; adjust that dependency if the distro uses a different service
name. For another init system, install with `--init none` and run
`/usr/local/libexec/ps5-bt-sync` after mounting the configured directories and
initializing the Bluetooth adapter, before starting `bluetoothd`.

For image packaging, `--destdir` stages the same files without enabling services
or querying hardware. Without `--adapter`, the importer uses the only adapter
present at boot and imports nothing if there is more than one.

## Handoff

The loader writes `ps5-bt-sync.json` beside the resolved initrd, including when
`path-override.txt` changes the boot path. The importer reads that file from
`boot_directory` in its configuration, validates it against the configured and
live adapter, then merges it into BlueZ's store while `bluetoothd` is stopped.
Exports without a source adapter address use the configured, live-verified adapter.
An explicit source address must match the configured address.
Existing files are backed up before replacement. Failed writes trigger rollback.
Unchanged keys are not rewritten. The handoff is deleted after consumption,
including malformed input. Missing exports leave the store unchanged.

The version 2 JSON format contains `version`, `adapter`, `devices` and `skipped`.
Each device has `peer`, `name`, `class`, `type` and `key`; `type` is currently 4.
There are at most 32 devices and skipped records combined. Keys are 16 bytes,
encoded as uppercase hexadecimal. The importer rejects duplicate fields/devices,
unsupported versions and invalid values before changing any bonds.
`adapter` may be null when the loader does not provide the source address.

The registry layout and key type were tested on firmware 13.60 with a DualSense
and DualSense Edge. Other firmware and devices need testing. LE key formats are
not imported; unsupported active records are counted as skipped. The paired flag
excludes removed bonds even when PS5 OS retains their old keys.

The handoff contains pairing secrets on the boot partition. It is short-lived
but unencrypted, and deletion is not secure erasure on flash. Do not include
handoffs, BlueZ files or their backups in reports or image releases.

## Check and disable

On systemd, use `journalctl -u ps5-bt-sync.service`. On another init system, the
helper prints counts without keys. Keep `bluetoothd` stopped during a manual run.

To disable Linux import, disable the startup service. This keeps working Linux
bonds, but the loader still exports keys and the handoff remains until consumed
or removed. Restore a bond backup only while `bluetoothd` is stopped; an old key
may no longer match the controller.

## Tests

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s bluetooth/tests -v
```
