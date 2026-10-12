#!/usr/bin/env bash
# =============================================================================
# Deploy bản đã build sẵn trên GHCR lên server prod — chạy TRÊN SERVER, trong thư mục có
# compose.prod.yml + .env (vd ~/hcc). Chép tay lên server một lần: scp scripts/server_deploy.sh
# <user>@<server>:~/hcc/ && chmod +x ~/hcc/server_deploy.sh
#
# GitHub Actions gọi qua SSH bằng khoá deploy bị ép chạy đúng script này
# (authorized_keys: command="…/server_deploy.sh",no-pty,…) → tag nằm trong SSH_ORIGINAL_COMMAND.
# Chạy tay trên server:
#   ./server_deploy.sh v11.10.2026     # deploy tag (kéo image từ GHCR)
#   ./server_deploy.sh rollback        # quay về bản chạy ngay trước đó (:prev)
#
# Chỉ đổi image của app / fe / monitor-fe: KHÔNG down, KHÔNG đụng service mongo, .env, ./data.
# /healthz không lên đúng bản trong HEALTH_TIMEOUT giây → tự quay về :prev và thoát lỗi.
# =============================================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

REGISTRY="${DEPLOY_REGISTRY:-ghcr.io/dev-f19}"
COMPOSE=(docker compose -f compose.prod.yml)
IMAGES=(autofill-hcc-be autofill-hcc-fe autofill-hcc-monitor-fe)
SERVICES=(app fe monitor-fe)
# vNgày.Tháng.Năm[.lần]: v11.10.2026, v11.10.2026.1 — khớp đúng mẫu mới chạy, chặn mọi chuỗi lạ
# lọt qua SSH (tag còn được ghép vào tên image).
TAG_RE='^v(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.20[0-9]{2}(\.[1-9][0-9]{0,2})?$'
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
KEEP_TAGS=3   # số tag GHCR giữ lại trên đĩa cho mỗi image (đỡ đầy ổ, vẫn quay về được vài bản)
HISTORY=deploy-history.log

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }

arg="${1:-${SSH_ORIGINAL_COMMAND:-}}"
if [[ "$arg" != "rollback" && ! "$arg" =~ $TAG_RE ]]; then
  log "Tham số không hợp lệ: '${arg}'. Dùng: server_deploy.sh vDD.MM.YYYY[.n] | rollback"
  exit 2
fi

# Một lượt deploy tại một thời điểm (Actions chạy chồng hoặc người chạy tay cùng lúc).
exec 9>.deploy.lock
flock -n 9 || { log "Đang có lượt deploy khác chạy — thử lại sau."; exit 3; }

APP_PORT="$(grep -E '^PORT=' .env 2>/dev/null | tail -1 | cut -d= -f2 | tr -d "\"' \r")"
APP_PORT="${APP_PORT:-8000}"

# Chờ BE trả /healthz (đúng version nếu truyền vào) và 2 web trả 200.
healthy() {
  local want="$1" body i
  for ((i = 0; i < HEALTH_TIMEOUT / 3; i++)); do
    body="$(curl -fsS --max-time 3 "http://127.0.0.1:${APP_PORT}/healthz" 2>/dev/null || true)"
    if [[ "$body" == *'"ok":true'* ]] \
      && { [[ -z "$want" ]] || [[ "$body" == *"\"version\":\"${want}\""* ]]; } \
      && curl -fsS --max-time 3 -o /dev/null http://127.0.0.1:12006/ \
      && curl -fsS --max-time 3 -o /dev/null http://127.0.0.1:12007/; then
      log "healthz: ${body}"
      return 0
    fi
    sleep 3
  done
  log "healthz lần cuối: ${body:-<không phản hồi>}"
  return 1
}

restart_services() {
  # --no-deps: không đụng mongo; --no-build: compose có `build:` nhưng server không có mã nguồn.
  "${COMPOSE[@]}" up -d --no-build --no-deps "${SERVICES[@]}"
}

image_id() { docker image inspect --format '{{.Id}}' "$1" 2>/dev/null || true; }

rollback_to_prev() {
  local img
  for img in "${IMAGES[@]}"; do
    if [[ -z "$(image_id "${img}:prev")" ]]; then
      log "Không có ${img}:prev để quay về — dừng, cần xử lý tay."
      return 1
    fi
  done
  for img in "${IMAGES[@]}"; do docker tag "${img}:prev" "${img}:latest"; done
  restart_services
  healthy ""
}

# shellcheck disable=SC2329  # gọi gián tiếp qua `declare -f` trong tiến trình dọn chạy nền
prune_old_tags() {
  local img tag
  for img in "${IMAGES[@]}"; do
    # `docker image ls` xếp mới → cũ; bỏ tag GHCR cũ (layer còn dùng bởi :latest/:prev không bị xoá).
    docker image ls "${REGISTRY}/${img}" --format '{{.Tag}}' | tail -n +$((KEEP_TAGS + 1)) |
      while read -r tag; do docker rmi "${REGISTRY}/${img}:${tag}" >/dev/null || true; done
  done
  docker image prune -f >/dev/null || true
}

if [[ "$arg" == "rollback" ]]; then
  log "ROLLBACK về bản chạy trước đó (:prev)"
  if rollback_to_prev; then
    echo "$(date '+%F %T') rollback OK" >>"$HISTORY"
    log "Đã quay về bản trước."
    exit 0
  fi
  echo "$(date '+%F %T') rollback LỖI" >>"$HISTORY"
  exit 1
fi

TAG="$arg"
log "DEPLOY ${TAG} từ ${REGISTRY}"
for img in "${IMAGES[@]}"; do docker pull -q "${REGISTRY}/${img}:${TAG}"; done

declare -A PREV_BEFORE=()
for img in "${IMAGES[@]}"; do
  PREV_BEFORE[$img]="$(image_id "${img}:prev")"
  # Deploy lại đúng bản đang chạy thì KHÔNG ghi đè :prev — kẻo mất đường quay về bản cũ thật.
  current="$(image_id "${img}:latest")"
  if [[ -n "$current" && "$current" != "$(image_id "${REGISTRY}/${img}:${TAG}")" ]]; then
    docker tag "${img}:latest" "${img}:prev"
  fi
  docker tag "${REGISTRY}/${img}:${TAG}" "${img}:latest"
done

restart_services
if healthy "$TAG"; then
  echo "$(date '+%F %T') ${TAG} OK" >>"$HISTORY"
  log "Xong: prod đang chạy ${TAG}."
  # Dọn image cũ có thể mất nhiều phút (ổ chứa nhiều bản deploy tay cũ) → chạy nền, tách khỏi phiên
  # SSH để Actions báo xong ngay. Đóng fd 9 (9>&-): KHÔNG giữ khoá deploy — rollback gấp ngay sau đó
  # không phải chờ dọn; khoá riêng .prune.lock chặn hai lượt dọn chồng nhau. Dọn chỉ xoá image không
  # tên + tag GHCR cũ, không đụng :latest/:prev hay bản đang kéo về.
  nohup bash -c "$(declare -f log prune_old_tags); REGISTRY='${REGISTRY}' KEEP_TAGS=${KEEP_TAGS}; \
    IMAGES=(${IMAGES[*]}); exec 8>.prune.lock; flock -n 8 || exit 0; prune_old_tags" \
    >>prune.log 2>&1 </dev/null 9>&- &
  exit 0
fi

log "${TAG} không lên được — tự quay về bản trước."
if rollback_to_prev; then
  # :prev lúc này trùng bản đang chạy → trả lại :prev cũ để `rollback` tay vẫn lùi thêm được một bản.
  for img in "${IMAGES[@]}"; do
    [[ -n "${PREV_BEFORE[$img]}" ]] && docker tag "${PREV_BEFORE[$img]}" "${img}:prev"
  done
  echo "$(date '+%F %T') ${TAG} LỖI → đã quay về :prev" >>"$HISTORY"
else
  echo "$(date '+%F %T') ${TAG} LỖI → quay về :prev cũng LỖI" >>"$HISTORY"
fi
exit 1
