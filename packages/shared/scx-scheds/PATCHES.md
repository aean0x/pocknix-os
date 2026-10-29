# scx-scheds patches

What this package carries and why, one entry per patch. How each patch works is in its header.

## Base

upstream `v1.1.3` (c8728c6, 2026-08-19), pinned upstream Rust 1.99.0

Same workspace members as the base package; it shadows the base by repo order. Drop the package
once an upstream release carries 0002-0005.

Last rebased: 2026-10 (initial).

## Carried

All scx_lavd fixes, verbatim from upstream.

- **0001** The 1.1.3 runnable-task stall (scx #3750) is gone: the REENQ cached-CPU pick is checked
  against cpus_ptr. Source: upstream 6d31ddd, also in Arch 1.1.3-2.
- **0002** Neighbor migration fires on non-SMT machines. Source: upstream d762220.
- **0003** Autopilot switches modes: its configuration binding is fixed (without it autopilot never
  switches). Source: upstream 02ff6a5.
- **0004** 1.1.3's 3ff16ec micro-stutter is gone: the compete window scales by online CPUs.
  Source: upstream e6aab93, PR #3805.
- **0005** RT and DL tasks no longer flood the futex hooks with "no task data" errors.
  Source: upstream 0745c74.

## Not taken

- The cpuperf-target series (PR #3793: 1efce60, a6583f9, 64470c8, dd7aea8): lower clocks cost
  smoothness on this SoC, measured A/B on device.
- 7b0b432: overflow set on bursty wake-ups.
- d5b8c4f/fc2f4d2: guard the low-util bypass, off under --lb-local-dsq-util-pct 0.
- 888a907: slow path only without PREEMPT_RCU.
- 86714ed: futex prototypes unchanged on 7.2.
- 8a94a1f, a82c7bf and 4384169: they need main's sdt allocator rework (scx_free(),
  scx_task_free_rcu()).

## Retired numbers

None.
