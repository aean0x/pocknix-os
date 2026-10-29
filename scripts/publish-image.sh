#!/usr/bin/env bash
# Compress, checksum and upload the SD image for first installs (updates ship via the repo).
# The name is date-stamped because a public filename must never change bytes: CDN caches would
# mix chunks of two images into a corrupt flash. Config (config/pocknix.conf or env):
#   POCKNIX_IMAGE_RCLONE_REMOTE  rclone destination, e.g. r2:pocknix/images (empty = no upload)
#   POCKNIX_IMAGE_URL            public base URL, only used to print the download link
# build/ is root-owned after sudo builds: run with sudo -E if the output can't be written.

source "$(dirname "$0")/lib.sh"

IMG="${IMAGE_DIR}/pocknix-${SOC}-sd.img"
STAMP="$(date +%Y%m%d)"
OUT="${IMAGE_DIR}/pocknix-${SOC}-${STAMP}-sd.img.zst"

[ -f "${IMG}" ] || die "no ${IMG} — run 'make sd-image' first"
need_tool zstd
need_tool sha256sum

if [ ! -f "${OUT}" ] || [ "${IMG}" -nt "${OUT}" ]; then
  log "compressing $(du -h "${IMG}" | cut -f1) image -> $(basename "${OUT}") (zstd -12, all cores)"
  zstd -T0 -12 --force "${IMG}" -o "${OUT}" || die "zstd failed (root-owned ${IMAGE_DIR}? use sudo -E)"
else
  log "$(basename "${OUT}") is up to date — skipping compression"
fi

log "writing sha256"
( cd "${IMAGE_DIR}" && sha256sum "$(basename "${OUT}")" > "${OUT}.sha256" )
ok "prepared: $(basename "${OUT}") ($(du -h "${OUT}" | cut -f1)) + .sha256"

if [ -n "${POCKNIX_IMAGE_RCLONE_REMOTE}" ]; then
  need_tool rclone
  log "uploading -> ${POCKNIX_IMAGE_RCLONE_REMOTE}"
  # image first, checksum last: a visible .sha256 implies the image is complete
  rclone copy --progress "${OUT}" "${POCKNIX_IMAGE_RCLONE_REMOTE}/"
  rclone copy "${OUT}.sha256" "${POCKNIX_IMAGE_RCLONE_REMOTE}/"
  ok "uploaded"
  if [ -n "${POCKNIX_IMAGE_URL}" ]; then
    log "download link: ${POCKNIX_IMAGE_URL}/$(basename "${OUT}")"
  fi
else
  warn "POCKNIX_IMAGE_RCLONE_REMOTE unset — nothing uploaded (artifacts left in ${IMAGE_DIR})"
fi
