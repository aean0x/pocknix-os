#!/usr/bin/env bash
# Sign and publish a repo tree: the per-SoC [pocknix] or the SoC-neutral [pocknix-shared]
# (POCKNIX_REPO_SCOPE, lib.sh). The source is ${REPO_STAGE_DIR} from `make stage`, never the raw
# localrepo (scripts/stage-repo.sh says why); unchanged packages reuse the sigs staging mirrored.
#
# Config (config/pocknix.conf or env):
#   POCKNIX_REPO_GPG_KEY        signing key id/email (required unless --unsigned)
#   POCKNIX_REPO_RCLONE_REMOTE  rclone destination (optional: skip upload if empty)
# Modes:
#   (default)    publish ${REPO_STAGE_DIR}; needs the .staged-ok marker, consumed on success
#   --serve      LAN testing: serve build/localrepo/<soc> on http :8000, NEVER uploads
#   --unsigned   skip signing; --serve only (device needs SigLevel = Optional TrustAll)
# POCKNIX_PUBLISH_FROM=localrepo publishes the raw localrepo (a new SoC's first publish, disaster
# recovery): it signs, syncs and PRUNES the bucket to whatever the dir holds.
# Run as the owner of the GPG key and rclone remote, NO sudo. Never republish a filename with
# different bytes (client caches and signatures break): bump pkgrel.

source "$(dirname "$0")/lib.sh"

REPO_DB="${REPO_NAME}.db.tar.gz"
# Each SoC's tree is its own <remote>/<soc> (tuned packages share pkgnames across SoCs), published
# once per SoC; [pocknix-shared] is <remote>/shared, published once.
RCLONE_DEST="${POCKNIX_REPO_RCLONE_REMOTE:+${POCKNIX_REPO_RCLONE_REMOTE}/${REPO_SEG}}"
unsigned=0 serve=0
for a in "$@"; do
  case "$a" in
    --unsigned) unsigned=1 ;;
    --serve)    serve=1 ;;
    *) die "unknown arg: $a (known: --unsigned --serve)" ;;
  esac
done
[ "${unsigned}" -eq 0 ] || [ "${serve}" -eq 1 ] \
  || die "--unsigned is LAN-testing only — pair it with --serve (an unsigned upload would break every device)"

# --- publish source selection ------------------------------------------------
MARKER=""
if [ "${serve}" -eq 1 ]; then
  # LAN testing serves the raw build output (test packages are the point) and
  # never uploads, so nothing can leak to the live repo.
  SRC="${REPO_LOCALREPO_DIR}"
  RCLONE_DEST=""
  [ -d "${SRC}" ] || die "no ${SRC} — run 'make packages' first"
elif [ "${POCKNIX_PUBLISH_FROM:-stage}" = "localrepo" ]; then
  SRC="${REPO_LOCALREPO_DIR}"
  [ -d "${SRC}" ] || die "no ${SRC} — run 'make packages' first"
  warn "publishing the RAW localrepo (shared build output, bucket will be pruned to match it)"
  warn "diff it against the live db first if you have not already"
elif [ "${POCKNIX_PUBLISH_FROM:-stage}" = "stage" ]; then
  SRC="${REPO_STAGE_DIR}"
  MARKER="${REPO_STAGE_DIR}/.staged-ok"
  [ -f "${MARKER}" ] || die "no staged release — run 'make stage PKG=\"...\"' first
(publish sources ${REPO_STAGE_DIR}, never the raw localrepo; see scripts/stage-repo.sh)"
  stale="$(find "${SRC}" -name '*.pkg.tar.*' -newer "${MARKER}" -print -quit)"
  [ -z "${stale}" ] || die "stage dir changed after staging ($(basename "${stale}")) — re-run make stage"
else
  die "POCKNIX_PUBLISH_FROM=${POCKNIX_PUBLISH_FROM} (known: stage, localrepo)"
fi

shopt -s nullglob
# package files, excluding detached signatures (which match the same glob)
pkgs=()
for p in "${SRC}"/*.pkg.tar.*; do [[ "$p" == *.sig ]] || pkgs+=("$p"); done
[ "${#pkgs[@]}" -gt 0 ] || die "no packages in ${SRC}"

if [ "${unsigned}" -eq 0 ]; then
  [ -n "${POCKNIX_REPO_GPG_KEY}" ] || die "POCKNIX_REPO_GPG_KEY unset (or pass --unsigned for LAN testing)
  one-time key setup: gpg --quick-gen-key 'Pocknix Packaging <you@example.com>' ed25519 sign 2y"
  need_tool gpg
  log "signing ${#pkgs[@]} packages with ${POCKNIX_REPO_GPG_KEY}"
  for p in "${pkgs[@]}"; do
    # re-sign only when missing or older than the package (idempotent republish)
    if [ ! -f "${p}.sig" ] || [ "${p}" -nt "${p}.sig" ]; then
      gpg --detach-sign --no-armor --yes -u "${POCKNIX_REPO_GPG_KEY}" "${p}" \
        || die "gpg sign failed for ${p} (root-owned file? chown or sudo -E)"
    fi
  done
  log "rebuilding signed repo database"
  ( cd "${SRC}" && repo-add --sign --key "${POCKNIX_REPO_GPG_KEY}" -q "${REPO_DB}" "${pkgs[@]}" ) \
    || die "repo-add --sign failed (is repo-add installed? 'pacman' package on the VM)"
  # export the public key next to the repo so devices can fetch + lsign it
  gpg --export --armor "${POCKNIX_REPO_GPG_KEY}" > "${SRC}/pocknix-repo.gpg"
  ok "signed: packages + ${REPO_DB} + pocknix-repo.gpg"
else
  # no repo-add here: the localrepo db is already maintained by build-packages.sh
  warn "preparing UNSIGNED (LAN testing only — device stanza needs SigLevel = Optional TrustAll)"
fi

if [ -n "${RCLONE_DEST}" ]; then
  need_tool rclone
  log "syncing -> ${RCLONE_DEST}"
  # packages+sigs first, db last: a client never sees a db entry whose package isn't up yet.
  # -L: pocknix.db/.files are repo-add symlinks that rclone otherwise skips (the device 404s).
  rclone copy --include '*.pkg.tar.*' --exclude '*.old*' "${SRC}" "${RCLONE_DEST}"
  rclone copy -L --include "${REPO_NAME}.db*" --include "${REPO_NAME}.files*" --include 'pocknix-repo.gpg' \
    --exclude '*.old*' "${SRC}" "${RCLONE_DEST}"
  # prune package versions that no longer exist locally (keeps the bucket bounded)
  rclone sync -L --exclude '*.old*' --exclude '.staged-ok' "${SRC}" "${RCLONE_DEST}"
  # remove any *.old* already in the bucket (idempotent; harmless if none)
  rclone delete --include '*.old*' "${RCLONE_DEST}" 2>/dev/null || true
  # consume the staging marker: the next publish must go through a fresh
  # `make stage` (which re-mirrors live), so stale stagings cannot be re-shipped
  [ -n "${MARKER}" ] && rm -f "${MARKER}"
  ok "published to ${RCLONE_DEST}"
elif [ "${serve}" -eq 0 ]; then
  warn "POCKNIX_REPO_RCLONE_REMOTE unset — nothing uploaded (repo prepared in ${SRC})"
fi

if [ "${serve}" -eq 1 ]; then
  need_tool python3
  ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  # serve the PARENT dir: shipped stanzas point at <base>/<soc>, so the URL path
  # must include the SoC segment (matches images built with POCKNIX_REPO_URL=http://<vm-ip>:8000)
  log "serving ${BUILD_DIR}/localrepo on http://${ip:-<this-host>}:8000 (Ctrl-C to stop; nothing was uploaded)"
  log "device stanza:  [${REPO_NAME}]  SigLevel = Optional TrustAll  Server = http://${ip:-<vm-ip>}:8000/${REPO_SEG}"
  python3 -m http.server 8000 -d "${BUILD_DIR}/localrepo"
fi
