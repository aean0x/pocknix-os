# pocknix-turnip-arm patches

What this package carries and why, one entry per patch. How each patch works is in its header.

## Base

Pinned Mesa release tarballs plus one main snapshot, listed in the PKGBUILD

The series mesa itself ships is never pinned here (see `packages/soc/mesa/PATCHES.md`).

## Carried

- **0001** Older Mesa series build again on C23 glibc, which now declares once_flag in stdlib.h.
  Applies: only the series that lack it; prepare() dry-runs it first, since 26.x and some late
  25.x releases already carry it. Source: Mesa 179e744f (Dave Airlie).

## Not taken

None.

## Retired numbers

None.
