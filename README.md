# ps5-linux-patches

## Compilation

```bash
git clone https://github.com/ps5-linux/ps5-linux-patches
git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
cd linux
git checkout tags/v7.0.5
git apply ../ps5-linux-patches/linux.patch
cp ../ps5-linux-patches/.config .config
make -j$(nproc)
```

## Installation

In the same `linux` folder after compilation, do:

```bash
sudo make modules_install
sudo make install
```

If you use Arch Linux, then additionally do:

```bash
sudo mkinitcpio -k "$(make kernelrelease)" -g /boot/initrd.img-$(make kernelrelease) || true
```

If you are updating Linux on your external USB SSD or if you are directly booting into M.2 SSD, i.e. if you use `-m2` in `cmdline.txt`, then you have to update the files on the FAT32 partition of your USB drive:

```bash
sudo cp /boot/vmlinuz /boot/efi/bzImage
sudo cp /boot/initrd.img /boot/efi/initrd.img
```

If you are updating Linux on your M.2 SSD, but you do not directly boot into it, i.e. if you use `m2_exec.sh`, then you do need to do this step.


## TODO

- amdgpu smu driver to show correct gpu frequency and temperature
- ethernet driver for (mediatek?) 0x104d:0x9104
- xhci driver adjustment for 0x104d:0x9108 to enable bluetooth
- hdmi converter improvments: hdr, rgb range, 120hz

## Bugs

- screen save does not work properly
- hdmi audio output does not work on some monitors
- hdmi 1440p and 2160p video output does not work on some monitors
