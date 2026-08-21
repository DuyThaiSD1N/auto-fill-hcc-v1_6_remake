#!/usr/bin/env bash
# Đóng gói extension auto-fill-hcc thành .zip để nạp/phát hành, LOẠI file thừa (git, tests, docs, junk mac).
# Zip đặt manifest.json ở GỐC archive (đúng cho "Load packed" / upload store). Chạy: bash build-zip.sh
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"                 # thư mục extension (nơi chứa manifest.json)
VERSION="$(grep -oE '"version"[[:space:]]*:[[:space:]]*"[0-9.]+"' "$SRC/manifest.json" | grep -oE '[0-9.]+' | head -1)"
OUT="$SRC/../auto-fill-hcc-extension-v${VERSION:-dev}.zip"

rm -f "$OUT"
cd "$SRC"

# -r đệ quy, -X bỏ metadata mac (uid/gid...). Loại: git, junk mac, tests, docs, tài liệu, zip cũ, sourcemap,
# và chính script build này.
zip -r -X "$OUT" . \
  -x '.git/*' \
  -x '*/.DS_Store' -x '.DS_Store' \
  -x '__MACOSX/*' \
  -x 'tests/*' \
  -x 'docs/*' \
  -x '*.md' \
  -x '*.zip' \
  -x '*.map' \
  -x 'build-zip.sh' >/dev/null

echo "✅ Đã tạo: $OUT"
echo "   Dung lượng: $(du -h "$OUT" | cut -f1)"
echo "   Số file:    $(unzip -l "$OUT" | tail -1 | awk '{print $2}')"
echo "── Kiểm tra không lẫn file thừa (phải RỖNG) ──"
unzip -l "$OUT" | grep -E '\.git/|\.DS_Store|/tests/|/docs/|\.md$|\.map$' || echo "   (sạch — không có file thừa)"
echo "── manifest.json phải ở gốc archive ──"
unzip -l "$OUT" | grep -E ' manifest\.json$' || echo "   ⚠ KHÔNG thấy manifest.json ở gốc!"
