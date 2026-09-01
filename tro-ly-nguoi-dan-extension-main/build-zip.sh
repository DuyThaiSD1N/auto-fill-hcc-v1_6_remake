#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST_FILE="${SCRIPT_DIR}/manifest.json"
OUTPUT_DIR="$(dirname "${SCRIPT_DIR}")"

if ! command -v zip >/dev/null 2>&1; then
  echo "Lỗi: máy chưa cài lệnh zip." >&2
  exit 1
fi

if [[ ! -f "${MANIFEST_FILE}" ]]; then
  echo "Lỗi: không tìm thấy manifest.json tại ${SCRIPT_DIR}." >&2
  exit 1
fi

EXTENSION_VERSION="$(awk -F'"' '/"version"[[:space:]]*:/ { print $4; exit }' "${MANIFEST_FILE}")"
if [[ -z "${EXTENSION_VERSION}" ]]; then
  echo "Lỗi: không đọc được version trong manifest.json." >&2
  exit 1
fi

BUILD_TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
OUTPUT_FILE="${OUTPUT_DIR}/tro-ly-nguoi-dan-extension-v${EXTENSION_VERSION}-${BUILD_TIMESTAMP}.zip"

mkdir -p "${OUTPUT_DIR}"

(
  cd "${SCRIPT_DIR}"
  zip -rq "${OUTPUT_FILE}" . \
    -x '.git/*' \
       '.gitignore' \
       '.DS_Store' \
       'dist/*' \
       'tests/*' \
       'node_modules/*' \
       'build-zip.sh' \
       'README.md' \
       '*.zip'
)

echo "Đã tạo: ${OUTPUT_FILE}"
