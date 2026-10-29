# powerdevil patches

What this package carries and why, one entry per patch. How each patch works is in its header.

## Base

6.8.1 tarball (Arch's build, no kdoctools)

It shadows the base by repo order.

Last rebased: 2026-10-23 (6.8.1, base cut).

## Carried

- **0001** Plasma's lowest brightness stops at 5% instead of kwin's raw level 1, which is black on
  DCS-dimmed panels: internal panels report max/20 as the safe minimum. Source: armada 0001, code
  verbatim, message rewritten; upstream: not filed. Drop: the condition is in the patch header.

## Not taken

None.

## Retired numbers

None.
