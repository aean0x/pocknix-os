# PATCHES.md: patch ledger (what pocknix-os carries, on which base, and why)

Records only what this repo controls: the pinned base, the patch series carried today and
where each patch came from, plus anything deliberately not taken or kept dropped (one-clause
reason) so the next sync or rebase does not bring it back, and the retired numbers of a
series that never reuses them. Plain history (upstreamed, replaced, renamed, moved) lives
in git: `git log --follow -- <patch>` and this file's own log. Never restate another
project's state here (what armada or ROCKNIX pin or carry, who is ahead): it goes stale
the day they move and nobody re-checks. Read theirs live: armada =
`packages/kernel/PATCHES.md` + `patches/series` in armada-os/armada; ROCKNIX = the
`vendor/rocknix-<soc>` sync (the kernel rows below record the synced commit;
`kernel/<soc>/kernel.conf` pins the stock version).

## Index

| Component | Ledger | Base |
|---|---|---|
| kernel (common) | [kernel/common/PATCHES.md](kernel/common/PATCHES.md) | Each SoC's kernel, after the SoC's own stack |
| kernel (sm8550) | [kernel/sm8550/PATCHES.md](kernel/sm8550/PATCHES.md) | Stock 7.2.10 + ROCKNIX `next` 6103571f67 (2026-10-11) |
| kernel (sm8250) | [kernel/sm8250/PATCHES.md](kernel/sm8250/PATCHES.md) | Stock 7.2.10 + ROCKNIX `next` 6103571f67 (2026-10-11) |
| gamescope | [packages/soc/gamescope/PATCHES.md](packages/soc/gamescope/PATCHES.md) | Valve `3.16.31` (f6916aa, 2026-09-27) |
| mesa | [packages/soc/mesa/PATCHES.md](packages/soc/mesa/PATCHES.md) | 26.2.4 tarball, epoch=2 |
| pocknix-turnip-arm | [packages/soc/pocknix-turnip-arm/PATCHES.md](packages/soc/pocknix-turnip-arm/PATCHES.md) | Pinned Mesa release tarballs plus one main snapshot, listed in the PKGBUILD |
| mangohud | [packages/shared/mangohud/PATCHES.md](packages/shared/mangohud/PATCHES.md) | v0.8.4, one shared untuned build |
| fex-emu | [packages/shared/fex-emu/PATCHES.md](packages/shared/fex-emu/PATCHES.md) | `896a8691` (FEX-2610 + its clang 23 thunkgen fix, 2026-10-12), one shared build |
| pocknix-mesa-android | [packages/shared/pocknix-mesa-android/PATCHES.md](packages/shared/pocknix-mesa-android/PATCHES.md) | 26.2.4 tarball (mesa's pin), epoch=2 |
| steamos-manager | [packages/shared/steamos-manager/PATCHES.md](packages/shared/steamos-manager/PATCHES.md) | upstream `8e2883d` (v26.4.1-12, 2026-09-17), pinned upstream Rust 1.99.0 |
| scx-scheds | [packages/shared/scx-scheds/PATCHES.md](packages/shared/scx-scheds/PATCHES.md) | upstream `v1.1.3` (c8728c6, 2026-08-19), pinned upstream Rust 1.99.0 |
| powerdevil | [packages/shared/powerdevil/PATCHES.md](packages/shared/powerdevil/PATCHES.md) | 6.8.1 tarball (Arch's build, no kdoctools) |
| gtk2 | [packages/shared/gtk2/PATCHES.md](packages/shared/gtk2/PATCHES.md) | gtk+ 2.24.33 tarball |

## Not yet split

| Component | pocknix-os base | Patches (pocknix-os) | Last rebased |
|---|---|---|---|
| alsa-ucm (RetroidPocket, sm8250) | ROCKNIX alsa-ucm-conf patches/SM8250/0002 | hand-ported into devices/sm8250/.../pocknix-bsp-sm8250 (conf.d symlink names from 0002 plus the RP5 legacy-loader name from their 0003; UCM is NOT covered by make sync, re-diff on a ROCKNIX pin bump); wsa881x stereo remap INLINED into RetroidPocket.conf (upstream file-conflict avoidance); local: no PlaybackMixerElem on the Speaker device (PipeWire must not drive the PA as volume), DisplayPort device in HiFi-RP.conf borrows the speaker's MultiMedia2 (a separate DP PCM fails PipeWire's probe and drops the HiFi profile), DP sink pinned to S16LE by 52-retroid-pocket-5-hdmi.conf (24-bit DP port start times out) | 2026-07 (initial port) |
| alsa-ucm (AYN-Odin2 + AYN-Thor, sm8550) | ROCKNIX alsa-ucm-conf patches/SM8550/0001_Add-AYN-Odin2 + 0005_Add-AYN-Thor | hand-ported into devices/sm8550/packages/pocknix-bsp-sm8550 (root/usr/share/alsa/ucm2/AYN/Odin2/ and AYN/Thor/; author credits kept in the files). UCM is NOT covered by make sync: re-diff against those patches on a ROCKNIX pin bump | never (hand-ported) |
| speaker DSP profile (RP5) | kokoko3k/jdsp4rp5.app README GraphicEQ (measured: calibration mic + REW) `480 0; 600 -5; 700 -16; 1000 -18; 1200 -10; 1670 -10; 2160 -18; 2800 -18; 3800 -28; 5000 -7; 7000 0` | devices/sm8250/packages/pocknix-bsp-sm8250/root/usr/share/pocknix/speaker-dsp/rp5.conf: the GraphicEQ fitted to 8 cut-only peaking bands by scripts/fit-graphiceq.py; high-pass 400 Hz added just under the speakers' floor, picked by ear; width 2.0 and limiter -0.1 dB / 500 ms as published; post gain +12 dB by ear on Linux, not the published +15 dB (that ran on Android's +16 dB digital gain) | 2026-10-27 |
| speaker DSP profile (Flip 2) | kokoko3k/jdsp4rp5.app README Flip 2 base GraphicEQ (measured) `347 0; 450 -4.5; 500 -8; 600 -4.5; 1015 -17.5; 1500 -13; 2300 -8; 4000 -8.5; 6000 -13.5; 7000 -16.5; 8500 -22.5; 11000 -12; 12000 -4; 16000 0` | devices/sm8250/packages/pocknix-bsp-sm8250/root/usr/share/pocknix/speaker-dsp/rpflip2.conf: the base curve (not the "sparkling" variants) fitted to 8 cut-only peaking bands by scripts/fit-graphiceq.py; high-pass 350 Hz at the speakers' floor; width 2.0 and limiter -0.1 dB / 500 ms as published; post gain +10 dB = the EQ's pink-noise level loss, not the published +15 dB (no one has listened on Linux) | 2026-10-27 |
| speaker DSP profile (RP6) | Ryan Retro, "Retroid Pocket 6 Speakers Fixed" (YouTube, 2026-02-18) description GraphicEQ `62 -11.5; 125 -9.8; 250 -0.1; 500 -9.9; 1000 -16.1; 2000 -16.9; 4000 -10.8; 8000 0.0; 16000 -3.5` | devices/sm8550/packages/pocknix-bsp-sm8550/root/usr/share/pocknix/speaker-dsp/rp6.conf: the GraphicEQ fitted to 8 cut-only peaking bands by scripts/fit-graphiceq.py (200 Hz-16 kHz), plus a -6 dB Q 1.4 band at 3.5 kHz (harshness); high-pass 200 Hz, width 2.0 and the 3.5 kHz band picked by ear on Linux; limiter -0.1 dB / 500 ms as on the RP5; post gain +9 dB by ear on Linux, 3 dB over the chain's level loss measured on game audio (no published value) | 2026-10-27 |
| InputPlumber maps (sm8250) | ROCKNIX devices/SM8250 01-retroid-controller.yaml + their shared retroid_mcu capability map | devices/sm8250/packages/pocknix-bsp-sm8250: rp5-gamepad.yaml = retroid_mcu minus LeftPaddle1/RightPaddle1, BTN_BACK -> QuickAccess (theirs: KeyF1), target deck (theirs: ds5); 01-retroid-flip2-controller.yaml + rpflip2-gamepad.yaml = our fork with the Guide+A QuickAccess chord (the Flip 2 has no back button). Not covered by make sync | never (hand-ported) |
| InputPlumber maps (sm8550) | ROCKNIX devices/SM8550 02-ayn-controller.yaml pattern + armada ayn_mcu capability map | devices/sm8550/packages/pocknix-bsp-sm8550: 01-rsinput-controller.yaml adds the gpio-keys grab (back paddles as L4/L5, volume-up re-emitted on the keyboard target) and the Nova match; sm8550-gamepad.yaml = ayn_mcu adapted; 02-ayn-thor-controller.yaml + thor-gamepad.yaml ours. Not covered by make sync | never (hand-ported) |
| sysctl 60-pocknix-gaming.conf | armada 60-armada-gaming.conf | overlay/usr/lib/sysctl.d/60-pocknix-gaming.conf, values as armada's (vm.swappiness=180 for the zram swap, watchdogs off); overlay/etc/systemd/zram-generator.conf pairs with it | never (hand-ported) |
| format-device.sh (pocknix-sdcard-automount) | Valve jupiter-hw-support /usr/lib/hwsupport/format-device.sh | packages/shared/pocknix-sdcard-automount/format-device.sh: mmcblk only (sda is the internal UFS disk), owner 1000:1000 kept so a card stays writable on a SteamOS device; pocknix-steamos-shim's steamos-format-device fronts it | never (hand-ported) |
| firmware (sm8550) | ROCKNIX/extra-firmware `30c56e2f` `SM8550/` (incl. the Thor ADSP pair from ROCKNIX 47e077d0bb, the Thor charging fix), per-file sha256 in devices/sm8550/packages/pocknix-firmware-sm8550 | none (blobs as-is, under /usr/lib/firmware/updates/). Not taken: `qcom/sm8550/ayaneo/` (no board in boards/models). Bump = new pin + `updpkgsums` | 2026-10-18 (Thor ADSP pair) |
| GRUB (sm8250 arm-efi) | ROCKNIX-built bootaa64.efi, VENDORED binary from release 20260701 (sha pinned; packages/soc/pocknix-bootloader-sm8250/README.provenance) | none (their 2.14-rc1 + 5 patches, used as-is); pocknix-authored grub.cfg template | 2026-07 (initial vendor) |
