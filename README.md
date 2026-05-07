# ps5-linux-patches

## Compilation

```bash
git clone https://github.com/ps5-linux/ps5-linux-patches
git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
cd linux
git checkout tags/v7.0.3
git apply ../ps5-linux-patches/linux.patch
cp ../ps5-linux-patches/.config .config
make -j16
```

## Installation (Ubuntu)

In the same `linux` folder after compilation, do:

```bash
sudo make modules_install
sudo make install
```

If you are updating Linux on your external USB SSD or you are directly booting into M.2 SSD, i.e. you use `-m2` in `cmdline.txt`, then you have to update the files on the FAT32 partition of your USB drive:

```bash
sudo mv /boot/efi/bzImage /boot/efi/bzImage.old
sudo mv /boot/efi/initrd.img /boot/efi/initrd.img.old
sudo cp /boot/vmlinuz-$(uname -r) /boot/efi/bzImage
sudo cp /boot/initrd.img-$(uname -r) /boot/efi/initrd.img
```

If you are updating Linux on your M.2 SSD, but you do not directly boot into it, i.e. if you use `m2_exec.sh`, then you do need to do this step.

## Compilation and Installation (Arch Linux)

Since Arch Linux is different on how the kernel is built, here are some updated commands for compiling
```bash
git clone https://github.com/ps5-linux/ps5-linux-patches
git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
cd linux
git checkout tags/v7.0.3
git apply ../ps5-linux-patches/linux.patch
cp ../ps5-linux-patches/.config .config
make olddefconfig
make -j$(nproc)
```

In the same `linux` folder after compilation, do:

```bash
sudo make modules_install
sudo make install
```

Then generate the initrd:

```bash
sudo mkinitcpio -k "$(make kernelrelease)" -g /boot/initrd.img-$(make kernelrelease) || true
```

If you are updating Linux on your external USB SSD or you are directly booting into M.2 SSD, i.e. you use `-m2` in `cmdline.txt`, then you have to update the files on the FAT32 partition of your USB drive:

```bash
sudo mv /boot/efi/bzImage /boot/efi/bzImage.old
sudo mv /boot/efi/initrd.img /boot/efi/initrd.img.old
sudo cp ~/linux/arch/x86/boot/bzImage /boot/efi/bzImage
sudo cp /boot/initrd.img-$(make kernelrelease) /boot/efi/initrd.img
sync
```

If you are updating Linux on your M.2 SSD, but you do not directly boot into it, i.e. if you use `m2_exec.sh`, then you do not need to do this step.


## TODO

- amdgpu smu driver to show correct gpu frequency and temperature
- ethernet driver for (mediatek?) 0x104d:0x9104
- xhci driver adjustment for 0x104d:0x9108 to enable bluetooth
- wlan driver marvell 1b4b:2b56 (https://github.com/nxp-imx/mwifiex)
- hdmi converter improvments: hdr, rgb range, 120hz

## Bugs

- screen save does not work properly
- hdmi audio output does not work on some monitors
- hdmi 1440p and 2160p video output does not work on some monitors
