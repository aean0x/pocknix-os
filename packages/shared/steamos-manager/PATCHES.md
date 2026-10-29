# steamos-manager patches

What this package carries and why, one entry per patch. How each patch works is in its header.

## Base

upstream `8e2883d` (v26.4.1-12, 2026-09-17), pinned upstream Rust 1.99.0

Rust is pinned because the locked base has no rust.

Last rebased: 2026-10 (initial).

## Carried

### Remotes (pocknix-perfd)

- **0001** CpuScaling1 can be served by a remote. Source: armada 0010, user.rs import hunk rebased
  by hand.
- **0004** Clients no longer see stale values from a remote already on the bus at configure time:
  the property relay starts for it too. Source: ours.
- **0007** The user daemon no longer deadlocks when a configured remote comes up after startup:
  configured remotes stay exported across owner changes (re-adding one from the owner-change task
  deadlocked it). Source: ours.

### Devices and services

- **0002** InputPlumber targets are only managed when configured. Source: armada 0011, verbatim.
- **0003** Wifi no longer goes dead when Steam asks to switch the backend: the switch is a no-op.
  Source: ours.
- **0005** A DualSense no longer goes silent once Steam starts: ds_inhibit defaults to off.
  Source: ours.
- **0006** speech-dispatcher is an optional default feature; we build without it. Source: ours.

## Not taken

- The Steam Frame series (devfreq GPU driver, custom platform profiles): pocknix-perfd serves
  those interfaces over remotes.d.

## Retired numbers

None.
