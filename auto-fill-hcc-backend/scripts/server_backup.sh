#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

DB="${BACKUP_DB:-autofill_hcc}"
CMD="${SSH_ORIGINAL_COMMAND:-$*}"

dump() {
  docker compose -f compose.prod.yml exec -T mongo sh -c \
    'mongodump -u "$MONGO_INITDB_ROOT_USERNAME" -p "$MONGO_INITDB_ROOT_PASSWORD" \
       --authenticationDatabase admin --db "$1" \
       --excludeCollection ws_events --excludeCollection ocr_cache \
       --archive --gzip --quiet' _ "$DB"
}

case "$CMD" in
  mongo)
    dump
    ;;
  save)
    if [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then echo "save chỉ chạy tại server" >&2; exit 2; fi
    dir="${BACKUP_LOCAL_DIR:-$PWD/backups}"
    out="$dir/$DB-$(date +%F-%H%M).archive.gz"
    mkdir -p "$dir"
    trap 'rm -f "$out.part"' EXIT
    dump > "$out.part"
    gzip -t "$out.part"
    mv "$out.part" "$out"
    chmod 600 "$out"
    echo "$(date '+%F %T') xong: $out $(du -h "$out" | cut -f1)"
    find "$dir" -name "$DB-*.archive.gz" -mtime +"${BACKUP_LOCAL_KEEP_DAYS:-7}" -print -delete
    ;;
  "rsync --server --sender "*)
    exec rrsync -ro "$PWD/data/uploads/consent"
    ;;
  *)
    echo "dùng: mongo | rsync (kéo consent)" >&2
    exit 2
    ;;
esac
