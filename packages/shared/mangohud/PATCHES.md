# mangohud patches

What this package carries and why, one entry per patch. How each patch works is in its header.

## Base

v0.8.4, one shared untuned build

Last rebased: 2026-10-14 (0.8.4 bump, moved to shared).

## Carried

### Readouts on Qualcomm

- **0001** MangoHud reads the Qualcomm GPU. Source: ROCKNIX, verbatim.
- **0002** The GPU devfreq node is found at runtime: kgsl-3d0, else the first
  `/sys/class/devfreq/*.gpu`. Source: armada 0002, their per-SoC path list replaced by the lookup.
- **0003** The battery shows its name. Source: ROCKNIX, verbatim.
- **0004** Battery power comes from power_now. Source: ROCKNIX, verbatim.
- **0005** RAM shows its name. Source: ROCKNIX, verbatim.
- **0007** GPU temperature is the hottest hwmon zone whose name has `gpu`. Source: ours.

### mangoapp

- **0006** mangoapp paces its redraws to gamescope's frame messages instead of free-running.
  Source: ours. Drop: at a release carrying upstream 2c1dc528.
- **0008** An unreadable fdinfo skips that process instead of aborting mangoapp.
  Source: armada 0007, verbatim.

## Not taken

- armada 0006 SM8750 battery time: it changes the readout on every board exposing
  `time_to_empty_avg`.
- armada 0008 active upscaler: it needs gamescope's extended mangoapp message.

## Retired numbers

None.
