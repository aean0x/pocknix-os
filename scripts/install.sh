#!/usr/bin/env bash
# An internal install repartitions the device's UFS and clones the *running* system, so it cannot
# run on the build host: it ships in pocknix-tools as /usr/bin/pocknix-install-internal.

source "$(dirname "$0")/lib.sh"
die "Run the installer ON THE DEVICE, not the build host:
    pocknix-install-internal --dry-run     # review the plan
    pocknix-install-internal               # install
See packages/shared/pocknix-tools/pocknix-install-internal."
