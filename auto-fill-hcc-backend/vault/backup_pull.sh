#!/usr/bin/env bash
set -euo pipefail

here="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
env_file="${BACKUP_ENV:-$here/backup.env}"
if [ -f "$env_file" ]; then set -a; . "$env_file"; set +a; fi

: "${BACKUP_SSH:?thiếu BACKUP_SSH trong backup.env}"
key="${BACKUP_SSH_KEY:-$HOME/.ssh/id_ed25519}"
dir="${BACKUP_DIR:-$HOME/backup/hcc}"
keep="${BACKUP_KEEP_DAYS:-14}"
ssh_cmd="ssh -i $key -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=30"

mkdir -p "$dir/mongo" "$dir/consent"
exec 9>"$dir/.lock"
flock -n 9 || { echo "$(date '+%F %T') bản trước chưa chạy xong, bỏ lượt này"; exit 1; }

out="$dir/mongo/autofill_hcc-$(date +%F-%H%M).archive.gz"
trap 'rm -f "$out.part"' EXIT

echo "$(date '+%F %T') bắt đầu"
$ssh_cmd "$BACKUP_SSH" mongo > "$out.part"
gzip -t "$out.part"
mv "$out.part" "$out"
echo "$(date '+%F %T') mongo xong: $(du -h "$out" | cut -f1)"

rsync -a --partial -e "$ssh_cmd" "$BACKUP_SSH:./" "$dir/consent/"
echo "$(date '+%F %T') consent xong: $(find "$dir/consent" -type f | wc -l) file, $(du -sh "$dir/consent" | cut -f1)"

find "$dir/mongo" -name 'autofill_hcc-*.archive.gz' -mtime +"$keep" -print -delete
echo "$(date '+%F %T') xong"
