#!/usr/bin/env bash
# check.sh — sanity-check the project + (when present) the built artifacts.
# Phase 0: validates the harness itself; later phases add image/DTB/module checks.

source "$(dirname "$0")/lib.sh"

fail=0
note() { printf '  %-44s %s\n' "$1" "$2"; }

log "pocknix-os preflight"

# --- host tooling ----------------------------------------------------------
for t in bash sed rsync curl tar; do
  if have "$t"; then note "host tool: $t" "ok"; else note "host tool: $t" "MISSING"; fail=1; fi
done
if [ "$(uname -s)" = "Linux" ]; then note "host os" "Linux ok"
else note "host os" "$(uname -s) (image build needs Linux)"; fi

# --- project layout --------------------------------------------------------
for d in config config/packages scripts packages/shared packages/soc vendor "devices/${DEVICE}"; do
  [ -d "${POCKNIX_ROOT}/${d}" ] && note "dir: ${d}/" "ok" || { note "dir: ${d}/" "MISSING"; fail=1; }
done

# --- package placement: shared/ vs soc/ -------------------------------------
# The split is load-bearing: shared/ builds once into [pocknix-shared], soc/
# builds per SoC gated by ./socs. A PKGBUILD directly under packages/ is
# invisible to the build; a soc/ package without socs (or with an unknown SoC)
# would silently vanish from every repo; a socs file under shared/ is a
# misplacement (shared builds must be SoC-blind).
while IFS= read -r p; do
  note "package: ${p#"${POCKNIX_ROOT}"/}" "OUTSIDE shared/ and soc/ — never built"; fail=1
done < <(find "${POCKNIX_ROOT}/packages" -maxdepth 2 -name PKGBUILD \
           ! -path "*/packages/shared/*" ! -path "*/packages/soc/*" 2>/dev/null)
for p in "${POCKNIX_ROOT}"/packages/soc/*/; do
  [ -d "${p}" ] || continue
  n="$(basename "${p}")"
  if [ ! -f "${p}/socs" ]; then
    note "soc pkg: ${n}" "MISSING socs file"; fail=1; continue
  fi
  read -r _socs < "${p}/socs"
  bad=0
  # "all" = every kernel/<soc>, so a new SoC needs no socs edits; it never mixes with names.
  if [ "${_socs}" = all ]; then note "soc pkg: ${n}" "socs: all"; continue; fi
  for s in ${_socs}; do
    [ -d "${POCKNIX_ROOT}/kernel/${s}" ] || { note "soc pkg: ${n}" "unknown SoC '${s}' in socs"; fail=1; bad=1; }
  done
  [ "${bad}" -eq 0 ] && [ -n "${_socs}" ] && note "soc pkg: ${n}" "socs: ${_socs}"
done
for p in "${POCKNIX_ROOT}"/packages/shared/*/socs; do
  [ -e "${p}" ] || continue
  note "shared pkg: $(basename "$(dirname "${p}")")" "has a socs file (shared builds are SoC-blind — move it to packages/soc/ or delete the file)"; fail=1
done
for f in config/pocknix.conf config/pacman.conf.in config/packages/base.list \
         "devices/${DEVICE}/profile.conf" "kernel/${SOC}/kernel.conf"; do
  [ -f "${POCKNIX_ROOT}/${f}" ] && note "file: ${f}" "ok" || { note "file: ${f}" "MISSING"; fail=1; }
done
note "device" "${DEVICE} (${DEVICE_PRETTY:-?}) on ${SOC}"

# --- scripts executable ----------------------------------------------------
for s in sync.sh bootstrap.sh build-image.sh build-kernel.sh build-packages.sh \
         build-sd-image.sh stage-repo.sh stage-check.sh publish-repo.sh install.sh check.sh; do
  [ -x "${POCKNIX_ROOT}/scripts/${s}" ] && note "exec: scripts/${s}" "ok" || { note "exec: scripts/${s}" "not +x"; fail=1; }
done

# --- pocknix-perfd factory profiles ---------------------------------------
if out="$(python3 "${POCKNIX_ROOT}/scripts/check-power-profiles.py" 2>&1)"; then note "power profiles" "ok"
else note "power profiles" "BROKEN"; printf '%s\n' "${out}" | sed 's/^/    /'; fail=1; fi

# --- SoC families: what a new SoC or board must carry (all SoCs, not just DEVICE) ----
# Each of these has shipped broken once or was only written down: a missing profile dies at
# build time, a board key a consumer reads falls back to RP6 values, an unreferenced board
# never loads, and a cmdline drift ships a boot image that disagrees with the on-device one.
REQUIRED_BOARD_KEYS="POCKNIX_DEVICE POCKNIX_SOC POCKNIX_PANEL_W POCKNIX_PANEL_H
  POCKNIX_PANEL_REFRESH POCKNIX_PANEL_ORIENT POCKNIX_PANEL_MM POCKNIX_DESKTOP_ROTATE
  POCKNIX_DESKTOP_SCALE POCKNIX_BIG_CORES POCKNIX_INTERNAL_DISK POCKNIX_BOOT_GPT_NAME
  POCKNIX_BOOT_FAT_LABEL POCKNIX_ROOT_LABEL"
for _k in "${POCKNIX_ROOT}"/kernel/*/; do
  _soc="$(basename "${_k}")"; _bad=""
  for _f in "devices/${_soc}/profile.conf" "config/tuning/${_soc}.conf" "kernel/${_soc}/kernel.conf"; do
    [ -f "${POCKNIX_ROOT}/${_f}" ] || _bad="${_bad} missing ${_f};"
  done
  grep -q "^| kernel (${_soc}" "${POCKNIX_ROOT}/PATCHES.md" || _bad="${_bad} no PATCHES.md kernel row;"
  _bsp="${POCKNIX_ROOT}/devices/${_soc}/packages/pocknix-bsp-${_soc}"
  [ -f "${_bsp}/device.conf" ] || _bad="${_bad} missing pocknix-bsp-${_soc}/device.conf;"
  for _b in "${_bsp}"/boards/*.conf; do
    [ -f "${_b}" ] || continue
    _n="$(basename "${_b}")"
    grep -qs "boards/${_n}" "${_bsp}/device.conf" "${_bsp}"/boards/*.conf || _bad="${_bad} ${_n} never sourced;"
    # Evaluated, not grepped: a variant board sources its base board.
    _r="$(sed "s|/usr/lib/pocknix/boards/|${_bsp}/boards/|g" "${_b}" | env -i bash -c '
      . /dev/stdin; for k in '"${REQUIRED_BOARD_KEYS//$'\n'/ }"'; do eval "[ -n \"\${${k}:-}\" ]" || printf "%s " "${k}"; done
      printf "|%s" "${POCKNIX_SOC:-}"')"
    _m="${_r%%|*}"; [ -z "${_m}" ] || _bad="${_bad} ${_n} lacks ${_m% };"
    [ "${_r#*|}" = "${_soc}" ] || _bad="${_bad} ${_n} says POCKNIX_SOC=${_r#*|};"
  done
  # Same evaluation as build-packages.sh's guard: shared config kept, this profile's own keys reset.
  _cmd="$(unset SOC ROOT_LABEL KERNEL_CMDLINE KERNEL_CMDLINE_ROOT KERNEL_CMDLINE_EXTRA
          . "${POCKNIX_ROOT}/devices/${_soc}/profile.conf"; printf '%s' "${KERNEL_CMDLINE}")"
  if [ -f "${_bsp}/kernel-cmdline" ]; then
    [ "$(cat "${_bsp}/kernel-cmdline")" = "${_cmd}" ] || _bad="${_bad} BSP kernel-cmdline drifted from the profile;"
  fi
  _grub="${POCKNIX_ROOT}/packages/soc/pocknix-bootloader-${_soc}/grub.cfg"
  if [ -f "${_grub}" ]; then
    while IFS= read -r _l; do
      [ "${_l}" = "${_cmd}" ] || { _bad="${_bad} a grub.cfg menuentry cmdline drifted from the profile;"; break; }
    done < <(sed -n 's|^[[:space:]]*linux /KERNEL ||p' "${_grub}")
  fi
  if [ -z "${_bad}" ]; then note "family: ${_soc}" "ok"; else note "family: ${_soc}" "${_bad# }"; fail=1; fi
done
# Every key a board sets is part of the runtime contract, so it must be in the README table.
_undoc=""
for _key in $(cat "${POCKNIX_ROOT}"/devices/*/packages/pocknix-bsp-*/boards/*.conf \
                  "${POCKNIX_ROOT}"/devices/*/packages/pocknix-bsp-*/device.conf 2>/dev/null |
              grep -oE '^[[:space:]]*POCKNIX_[A-Z0-9_]+=' | tr -d ' =' | sort -u); do
  grep -q "\`${_key}\`" "${POCKNIX_ROOT}/devices/README.md" || _undoc="${_undoc} ${_key}"
done
if [ -z "${_undoc}" ]; then note "board keys documented" "ok"
else note "board keys documented" "not in devices/README.md:${_undoc}"; fail=1; fi

# --- kernel enablement present? (committed; refreshable via sync) -----------
_npatch=$(find "${KERNEL_DIR}/patches" -name '*.patch' 2>/dev/null | wc -l | tr -d ' ')
if [ "${_npatch:-0}" -gt 0 ]; then
  note "kernel: enablement (kernel/${SOC}/)" "${_npatch} patches"
else
  note "kernel: enablement (kernel/${SOC}/)" "run 'make sync'"
fi
# vendor sync is build-time only (gitignored)
if [ -d "${VENDOR_DIR}/rocknix-${SOC}/reference" ]; then
  note "vendor: reference/firmware" "synced"
else
  note "vendor: reference/firmware" "run 'make sync' (build host)"
fi

# --- built artifacts (only checked if they exist) --------------------------
if [ -d "${KERNEL_BUILD_DIR}/out" ]; then
  note "kernel build" "$(cat "${KERNEL_BUILD_DIR}/out/kernelrelease" 2>/dev/null || echo present)"
else
  note "kernel build" "run 'make kernel'"
fi
if [ -f "${IMAGE_DIR}/KERNEL" ]; then
  note "boot image KERNEL" "$(du -h "${IMAGE_DIR}/KERNEL" | cut -f1) (qcom-abl)"
else
  note "boot image KERNEL" "not built (make kernel)"
fi
[ -d "${ROOTFS_DIR}" ] && note "rootfs" "present"

echo
[ "$fail" -eq 0 ] && ok "preflight passed" || die "preflight found problems (see above)"
