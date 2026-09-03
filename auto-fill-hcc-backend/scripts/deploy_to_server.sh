#!/usr/bin/env bash
# =============================================================================
# Deploy Auto Fill HCC sang server khác BẰNG DOCKER IMAGE — KHÔNG cần GitHub.
#
# Ý tưởng (đúng như anh Tuấn nói): GitHub chỉ là 1 cách đưa MÃ NGUỒN lên server
# rồi build tại đó. Ở đây ta build image MỘT LẦN, rồi bê NGUYÊN image sang server
# đích chạy. Server đích chỉ cần Docker + Docker Compose — KHÔNG cần mã nguồn,
# KHÔNG cần git, KHÔNG cần build lại.
#
# Script này CHỈ build + đẩy file (image tarball + compose.prod.yml) LÊN server đích.
# Việc NẠP image và CHẠY thì bấm ./server_up.sh (bạn tạo sẵn) trên server đích.
# Cách chuyển: docker save → scp (không cần registry riêng).
#
# DÙNG:
#   TARGET=user@server-dich ./scripts/deploy_to_server.sh
#   # rồi trên server đích:  cd <TARGET_DIR> && ./server_up.sh
#
# TÙY CHỌN (biến môi trường):
#   TARGET_DIR   thư mục đặt compose/.env ở server đích   (mặc định /opt/autofill-hcc)
#   PLATFORM     kiến trúc server đích                    (mặc định linux/amd64)
#   SEND_ENV=1   gửi luôn ./.env sang đích (secret!)      (mặc định 0 — đặt .env sẵn ở đích)
#   BUILD=0      bỏ qua bước build, dùng image đang có     (mặc định 1)
# =============================================================================
set -euo pipefail

TARGET="${TARGET:?Thiếu TARGET=user@host — server đích}"
TARGET_DIR="${TARGET_DIR:-/opt/autofill-hcc}"
PLATFORM="${PLATFORM:-linux/amd64}"
SEND_ENV="${SEND_ENV:-0}"
BUILD="${BUILD:-1}"
BE_IMG="autofill-hcc-be:latest"
FE_IMG="autofill-hcc-fe:latest"
MONITOR_FE_IMG="autofill-hcc-monitor-fe:latest"   # FE thứ 2 (Web Monitor :12007) — compose.prod.yml có build:./monitor-fe
TARBALL="autofill-hcc-images.tar.gz"

cd "$(cd "$(dirname "$0")/.." && pwd)"   # về thư mục auto-fill-hcc-backend (nơi có compose.prod.yml)

if [ "$BUILD" = "1" ]; then
  echo "==> 1/3 Build image cho $PLATFORM (be + fe + monitor-fe)"
  # buildx --platform để build ĐÚNG kiến trúc server đích, kể cả khi máy build là Mac ARM.
  docker buildx build --platform "$PLATFORM" -t "$BE_IMG" --load .
  docker buildx build --platform "$PLATFORM" -t "$FE_IMG" --load ./fe
  # FE thứ 2: KHÔNG đóng gói thì server đích cố build:./monitor-fe → lỗi thiếu mã nguồn.
  docker buildx build --platform "$PLATFORM" -t "$MONITOR_FE_IMG" --load ./monitor-fe
else
  echo "==> 1/3 Bỏ qua build (BUILD=0), dùng image đang có"
fi

echo "==> 2/3 Đóng gói 3 image thành 1 file nén"
docker save "$BE_IMG" "$FE_IMG" "$MONITOR_FE_IMG" | gzip > "$TARBALL"
ls -lh "$TARBALL"

echo "==> 3/3 Chuyển sang server đích: $TARGET:$TARGET_DIR"
ssh "$TARGET" "mkdir -p '$TARGET_DIR'"
# Chỉ đẩy tarball + compose. server_up.sh đã có sẵn trên server đích (chạy tay ở đó).
scp "$TARBALL" compose.prod.yml "$TARGET:$TARGET_DIR/"
if [ "$SEND_ENV" = "1" ]; then
  scp .env "$TARGET:$TARGET_DIR/"
else
  ssh "$TARGET" "test -f '$TARGET_DIR/.env'" \
    || echo "  ⚠  Server đích CHƯA có $TARGET_DIR/.env — hãy tạo trước khi chạy server_up.sh."
fi

rm -f "$TARBALL"
echo "✅ Đã đẩy xong. GIỜ TRÊN SERVER ĐÍCH chạy:"
echo "     cd $TARGET_DIR && ./server_up.sh"
echo "   (server_up.sh sẽ: docker load → compose up -d → ps → dọn tarball)"
