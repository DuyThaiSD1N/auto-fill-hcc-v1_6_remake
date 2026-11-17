#!/bin/bash
# Lệnh ép buộc (command="...") cho khoá SSH "auto-test-hcc local" trong ~/.ssh/authorized_keys của server.
# Khoá đó chỉ: mở đường hầm tới DUY NHẤT 127.0.0.1:12004 (Mongo, tài khoản role read) + chạy script này:
#   exists <b64>...   in "MISSING <b64>" cho từng tệp không có
#   cat <b64>         xuất nội dung một tệp
# Đường dẫn tương đối so với ROOT, mã hoá base64. Không theo symlink ra ngoài ROOT, không cho "..".
set -euo pipefail
set -f
ROOT="${AUTOTEST_UPLOADS_ROOT:-/home/nlp/hcc/data/uploads}"
read -r -a args <<< "${SSH_ORIGINAL_COMMAND:-}"
verb="${args[0]:-}"
case "$verb" in exists|cat) ;; *) echo "không cho phép" >&2; exit 1 ;; esac
for enc in "${args[@]:1}"; do
  rel="$(printf '%s' "$enc" | base64 -d 2>/dev/null)" || { echo "sai mã hoá" >&2; exit 1; }
  case "$rel" in /*|*..*|"") echo "đường dẫn lạ" >&2; exit 1 ;; esac
  real="$(realpath -e -- "$ROOT/$rel" 2>/dev/null)" || real=""
  if [ -z "$real" ] || [ ! -f "$real" ] || [ "${real#"$ROOT"/}" = "$real" ]; then
    if [ "$verb" = exists ]; then echo "MISSING $enc"; continue; fi
    echo "không có tệp" >&2; exit 2
  fi
  if [ "$verb" = cat ]; then exec cat -- "$real"; fi
done
