# ps5-linux-patches

- [Compilation](#compilation)
- [Installation](#installation)
- [TODO](#todo)
- [Bugs](#bugs)
- [Options](#options)
  - [No picture](#no-picture)
  - [HDMI](#hdmi)
  - [HDMI on VERDE](#hdmi-on-verde)
  - [USB-C DisplayPort](#usb-c-displayport)
  - [GPU](#gpu)
  - [Clock, fan and power](#clock-fan-and-power)
  - [TV and Bluetooth](#tv-and-bluetooth)
  - [PS5 Pro](#ps5-pro)

## Compilation

```bash
git clone https://github.com/ps5-linux/ps5-linux-patches
git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
cd linux
git checkout "tags/v$(grep -m1 "^# Linux/" ../ps5-linux-patches/.config | awk '{print $3}')"
git apply ../ps5-linux-patches/linux.patch
cp ../ps5-linux-patches/.config .config
make -j$(nproc)
```

## Installation

In the same `linux` folder after compilation, do:

```bash
sudo make modules_install && sudo make install
```

On a PS5 Pro, also install the Viola firmware service, see [firmware/README.md](firmware/README.md#viola-firmware-ps5-pro).

## TODO

- amdgpu smu driver to show correct gpu frequency and temperature on the base ps5

## Bugs

- screen save does not work properly
- hdmi audio output does not work on some monitors
- hdmi 1440p and 2160p video output does not work on some monitors

## Options

add them to `cmdline.txt`, space separated, they apply from the next boot.

the ones marked **live** can also be changed while running, and every option can be read back the same way:

```bash
cat /sys/module/hdmi/parameters/frl_4k120
echo 0 | sudo tee /sys/module/hdmi/parameters/frl_4k120
```

### No picture

if the tv or monitor stays black, try these one at a time:

1. `amdgpu.force_1080p=1` - only 1080p60
2. `hdmi.extended_modes=0` - only the stock modes (1080p60, 1080p120, 1440p, 4k60)
3. `hdmi.frl_4k120=0` - no frl, so no 4k100/120 and no 4:2:0
4. `video=DP-1:1920x1080@60` - start the console at a fixed mode (the hdmi port shows up as `DP-1`, see `ls /sys/class/drm`)

if a display keeps replugging or has no picture, also turn hdcp off in the PS5 OS settings, it carries over into linux.

### HDMI

| option | default | |
|---|---|---|
| `hdmi.extended_modes` | `1` | `0` stock modes only, `1` adds 1080p100, manual timings up to 297 mhz and 1440p144, `2` also makes them preferred |
| `hdmi.extended_tmds` | `0` | `1` manual timings above 297 mhz outside 1440p, for 1080p 144 hz+ monitors (untested) |
| `hdmi.frl_4k120` | `1` | `0` turns frl off. **live** |
| `hdmi.frl_yuv420` | `1` | frl 4:2:0, `0` off, `1` as a fallback, `2` preferred when the mode allows it. **live** |
| `hdmi.frl_recovery` | `1` | `0` no retry with the next format after an frl failure. **live** |
| `hdmi.frl_drop_ms` | `0` | reject an frl plan after two display drops within this many ms of the start, `0` off. **live** |
| `hdmi.frl_failed` | | `Y` after frl failed on this display, write `N` to try again (same as a replug). **live** |
| `hdmi.vrr` | `0` | `1` freesync vrr, for displays with a freesync range |
| `hdmi.allm` | `1` | `0` off, `1` while the content type is game, `2` always. **live** |
| `hdmi.allm_avi` | `1` | avi content type with allm, `0` it content game, `1` cleared while allm is on, `2` always cleared. **live** |
| `hdmi.hdcp_mode` | `3` | `-1` keep, `0` on, `1` off, `2` on with hdcp 2.2, `3` off with the hdcp 2.2 bit set. **live** |

read only status: `frl_rate`, `frl_rate_max`, `allm_sink`, `allm_valid`, `allm_active`, `recovery_status`.

### HDMI on VERDE

some consoles have the VERDE hdmi chip instead of FLAVA3, the boot log says `HDMI IC Type [VERDE]`.

> [!NOTE]
> these are all off by default and not tested on a VERDE console yet.
> with all of them off it works like before: 8 bit, 1080p60, 1440p and 4k60.

| option | default | |
|---|---|---|
| `hdmi.verde_infoframes` | `0` | `1` hdr, bt.2020 and rgb range signalling, and an avi for every mode. **live**, from the next mode set |
| `hdmi.verde_deep_colour` | `0` | `1` 10 and 12 bit where the hdmi clock allows it |
| `hdmi.verde_frl` | `0` | `1` frl, 4k100/120 at 4:2:2 and 4k60 deep colour |
| `hdmi.verde_vrr` | `0` | `1` vrr, for displays with hdmi vrr and a freesync range |
| `hdmi.verde_allm` | `0` | `1` allm, follows `hdmi.allm` |

### USB-C DisplayPort

#### Dock or monitor stays black

the front port only outputs to devices on sonys list. most docks and displays are found on their own, if yours isnt, add it:

```
usbc_dp.extra_device=1234:5678
```

thats the usb-pd vendor and product id of the dock or monitor, in hex.

> [!IMPORTANT]
> the ps5 cant read this id, you have to look it up on another computer.

on linux, plug the dock or monitor into a usb-c port and run:

```bash
cat /sys/class/typec/port*-partner/identity/id_header /sys/class/typec/port*-partner/identity/product
```

```
0x00001234    <- vendor id, the last 4 digits
0x56780000    <- product id, the first 4 digits
```

that gives `1234:5678`. the ids `lsusb` shows for the docks usb hub are often the same, but not always.
up to 5 devices, comma separated, `VID:PIDMIN-PIDMAX` for a range of products.

#### All options

| option | default | |
|---|---|---|
| `usbc_dp.enable` | `-1` | `-1` starts dp when a display is plugged in, `0` off, `1` at boot. use `0` when booting from a drive on the front usb-c port, starting dp resets the port |
| `usbc_dp.extra_device` | | see above |
| `usbc_dp.extra_flags` | `0` | flags for `extra_device`, bit 0 pd only, bit 1 caesar |
| `usbc_dp.probe_vendors` | | usb-c pd chip vendors to try after the displays own, comma separated hex |
| `usbc_dp.learn` | `0` | `1` adds the vendor of a display that reports dp not configured, whats found is in `learned`. **live** |
| `usbc_dp.dp_lanes` | `4` | `2` dp on 2 lanes |
| `usbc_dp.pdcon_mode` | `5` | usb-c controller mode, `5` normal, `3` detect only, `4` usb charging |
| `usbc_dp.probe_without_hpd` | `0` | `1` probe the display without a hotplug signal |
| `usbc_dp.aux`, `usbc_dp.hpd` | | aux and hpd index, `-1` takes it from the vbios |

### GPU

| option | default | |
|---|---|---|
| `amdgpu.gpu_recovery` | `-1` | `-1` resets a hung queue only, never the whole gpu (a full reset doesnt work on the ps5), `0` no recovery at all, `1` also allows the full reset |
| `amdgpu.force_1080p` | `0` | `1` only 1080p60 on hdmi |
| `amdgpu.ps5_sensors` | `1` | `0` no gpu clock and temperature sensors |
| `amdgpu.ps5_cu_unlock` | `0` | harvested cu unlock for testing, `1` probe, `2` se0/sh0, `3` all, `4` probe all |
| `ps5_gpufreq.temp_limit` | `85` | hottest soc temperature allowed, 50-95 c. **live** |

### Clock, fan and power

| option | default | |
|---|---|---|
| `ps5_rtc.enable` | `1` | `0` no rtc driver |
| `ps5_rtc.write` | `1` | `0` read only, setting the time doesnt save sonys clock correction anymore |
| `fan.restore_table` | `1` | `0` dont put the consoles fan table back at suspend and shutdown |

### TV and Bluetooth

| option | default | |
|---|---|---|
| `ps5_cec.one_touch_play` | `1` | `0` dont turn the tv on and switch it to the console at boot |
| `btusb.ps5_iw620_le` | `1` | `0` IW620 bluetooth without legacy le and host address resolution |
| `btusb.ps5_iw620_linkkey` | `1` | `0` IW620 bluetooth doesnt answer the repeated link key request after pairing |

### PS5 Pro

| option | default | |
|---|---|---|
| `amdgpu.ps5_viola_fw` | `1` | `0` always use the cyan skillfish firmware, not the viola one |
| `amdgpu.ps5_smu` | `1` | `0` no gpu clock and temperature with the viola firmware |
| `mp1.ps5_bapm_set` | `0` | bapm parameter set with the viola firmware, `0` auto, `1`-`3` |
