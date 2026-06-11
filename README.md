# ps5-linux-patches

## Usage

- Stable PS5 profile:

```bash
git clone https://github.com/bizkut/ps5-linux-patches
git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
cd linux
git checkout "tags/v$(grep -m1 "^# Linux/" ../ps5-linux-patches/.config | awk '{print $3}')"
git apply ../ps5-linux-patches/linux.patch
cp ../ps5-linux-patches/.config .config
make -j$(nproc)
```

- CachyOS BORE profile (for `ps5-linux-image` profile `ps5-cachyos-bore`):

```bash
git clone https://github.com/bizkut/ps5-linux-patches
cd linux-7.0.12-source-tree  # replace with your CachyOS Linux source tree
while read -r patch; do
  [ -z "$patch" ] && continue
  [ "${patch#\#}" = "$patch" ] || continue
  git apply "../ps5-linux-patches/$patch"
done < ../ps5-linux-patches/profiles/cachyos-7.0-bore/series
cp ../ps5-linux-patches/profiles/cachyos-7.0-bore/ps5.config .config
make -j$(nproc)
```

The profile directory is organized for future patch-set upgrades:

```text
profiles/
  cachyos-7.0-bore/
    ps5.config
    series
    patches/
      linux.patch
      0001-ps5-cpuclock.patch
```

`linux.patch` keeps the base PS5 compatibility surface for CachyOS. `0001-ps5-cpuclock.patch`
adds the kernel `drivers/ps5/mp1.c` + `drivers/ps5/power.c` path used by the
`ps5-cpufreq` driver and related GPU/telemetry controls.

## Upstream workflow

This repository keeps a small PS5 overlay for the PS5-specific cpuclock driver and
small companion packaging hooks. The upstream source is:

- https://github.com/ps5-linux/ps5-linux-patches

Keep your fork (`bizkut`) on top of upstream in `main`:

```bash
git remote add upstream https://github.com/ps5-linux/ps5-linux-patches
git fetch upstream
git checkout main
git rebase upstream/main
```

The CachyOS BORE profile lives under:

- `profiles/cachyos-7.0-bore/ps5.config`
- `profiles/cachyos-7.0-bore/series`
- `profiles/cachyos-7.0-bore/patches/linux.patch`
- `profiles/cachyos-7.0-bore/patches/0001-ps5-cpuclock.patch`

When upstream releases a new stable version, the typical update flow is:

```bash
git fetch upstream main
git checkout main
git rebase upstream/main
```

Then rebase/merge your CachyOS BORE profile changes on top if they no longer apply cleanly.

## Sync output for ps5-linux-image

To regenerate a single patch that ps5-linux-image can consume as part of its `cachyos-7.0-bore` patch stack:

```bash
git fetch upstream main
git diff --minimal upstream/main..main \
  profiles/cachyos-7.0-bore > ../ps5-linux-patches-cachyos-bore.patch
```

## Installation

In the same `linux` folder after compilation, do:

```bash
sudo make modules_install
sudo make install
```

## TODO

- amdgpu smu driver to show correct gpu frequency and temperature
- xhci driver adjustment for 0x104d:0x9108 to enable bluetooth
- hdmi converter improvements: hdr, rgb range, 120hz

## Bugs

- screen save does not work properly
- hdmi audio output does not work on some monitors
- hdmi 1440p and 2160p video output does not work on some monitors
