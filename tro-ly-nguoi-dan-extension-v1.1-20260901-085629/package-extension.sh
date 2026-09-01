#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"

for command_name in python3 zip unzip; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Lỗi: thiếu lệnh '$command_name'." >&2
    exit 1
  fi
done

VERSION="$(python3 -c 'import json; print(json.load(open("manifest.json", encoding="utf-8"))["version"])')"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

if [[ $# -gt 1 ]]; then
  echo "Cách dùng: ./package-extension.sh [duong-dan-file.zip]" >&2
  exit 1
fi

if [[ $# -eq 1 ]]; then
  OUTPUT="$1"
  [[ "$OUTPUT" = /* ]] || OUTPUT="$SCRIPT_DIR/$OUTPUT"
else
  OUTPUT="$(dirname -- "$SCRIPT_DIR")/tro-ly-nguoi-dan-extension-v${VERSION}-${TIMESTAMP}.zip"
fi

if [[ "$OUTPUT" != *.zip ]]; then
  echo "Lỗi: file đầu ra phải có đuôi .zip: $OUTPUT" >&2
  exit 1
fi

# Các entrypoint không nằm hết trong manifest: background tạo offscreen document,
# content.js nhúng sidebar, sidebar mở permission page. Thiếu một file là extension lỗi runtime.
ROOT_FILES=(
  manifest.json
  background.js
  content.js
  sidebar.html
  sidebar.css
  sidebar.js
  offscreen.html
  offscreen.js
  permission.html
  permission.js
  README.md
)

# Copy nguyên thư mục runtime để không bỏ sót helper, vendor hoặc asset được gọi động.
RUNTIME_DIRS=(
  api
  assets
  content
  lib
  services
  vendor
)

for path in "${ROOT_FILES[@]}" "${RUNTIME_DIRS[@]}"; do
  if [[ ! -e "$path" ]]; then
    echo "Lỗi: thiếu file/thư mục runtime bắt buộc: $path" >&2
    exit 1
  fi
done

# Kiểm tra mọi file local được manifest tham chiếu. Wildcard resources (vd assets/*)
# phải khớp ít nhất một file/thư mục thật.
python3 - <<'PY'
import glob
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
refs: set[str] = set()

refs.update((manifest.get("icons") or {}).values())
refs.update(((manifest.get("action") or {}).get("default_icon") or {}).values())
background = (manifest.get("background") or {}).get("service_worker")
if background:
    refs.add(background)
for block in manifest.get("content_scripts") or []:
    refs.update(block.get("js") or [])
    refs.update(block.get("css") or [])
for block in manifest.get("web_accessible_resources") or []:
    refs.update(block.get("resources") or [])

missing = []
for ref in sorted(refs):
    matches = glob.glob(str(root / ref)) if any(ch in ref for ch in "*?[") else [str(root / ref)]
    if not matches or not any(Path(match).exists() for match in matches):
        missing.append(ref)

if missing:
    raise SystemExit("Manifest tham chiếu file không tồn tại: " + ", ".join(missing))
print(f"✓ Manifest references: {len(refs)} mục hợp lệ")
PY

STAGE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tlnd-extension-package.XXXXXX")"
cleanup() {
  rm -rf -- "$STAGE_DIR"
}
trap cleanup EXIT INT TERM

for path in "${ROOT_FILES[@]}"; do
  cp -p -- "$path" "$STAGE_DIR/$path"
done
for path in "${RUNTIME_DIRS[@]}"; do
  cp -R -- "$path" "$STAGE_DIR/$path"
done

# Rác hệ điều hành không thuộc extension.
find "$STAGE_DIR" -name '.DS_Store' -type f -delete

# Kiểm tra src/href local trong các trang HTML sau khi đã stage.
STAGE_DIR="$STAGE_DIR" python3 - <<'PY'
import os
import re
from pathlib import Path

stage = Path(os.environ["STAGE_DIR"])
missing = []
pattern = re.compile(r'''(?:src|href)=["']([^"']+)["']''', re.I)
for html in stage.rglob("*.html"):
    for ref in pattern.findall(html.read_text(encoding="utf-8")):
        if ref.startswith(("http://", "https://", "data:", "#")):
            continue
        target = (html.parent / ref.split("?", 1)[0].split("#", 1)[0]).resolve()
        if not target.exists():
            missing.append(f"{html.relative_to(stage)} -> {ref}")
if missing:
    raise SystemExit("HTML tham chiếu file không có trong gói: " + ", ".join(missing))
print("✓ HTML references: đầy đủ")
PY

mkdir -p -- "$(dirname -- "$OUTPUT")"
rm -f -- "$OUTPUT"
(
  cd "$STAGE_DIR"
  zip -q -r "$OUTPUT" .
)

unzip -tq "$OUTPUT" >/dev/null
ZIP_ENTRY_LIST="$STAGE_DIR/zip-entries.txt"
unzip -Z1 "$OUTPUT" > "$ZIP_ENTRY_LIST"

if ! grep -Fxq 'manifest.json' "$ZIP_ENTRY_LIST"; then
  echo "Lỗi: manifest.json không nằm ở gốc file ZIP." >&2
  exit 1
fi

for path in "${ROOT_FILES[@]}"; do
  if ! grep -Fxq "$path" "$ZIP_ENTRY_LIST"; then
    echo "Lỗi: ZIP thiếu file bắt buộc: $path" >&2
    exit 1
  fi
done

ENTRY_COUNT="$(wc -l < "$ZIP_ENTRY_LIST" | tr -d ' ')"
SIZE_BYTES="$(wc -c < "$OUTPUT" | tr -d ' ')"

echo "✓ Đóng gói thành công"
echo "  File: $OUTPUT"
echo "  Version: $VERSION"
echo "  Entries: $ENTRY_COUNT"
echo "  Size: $SIZE_BYTES bytes"
