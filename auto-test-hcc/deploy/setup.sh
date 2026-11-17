#!/usr/bin/env bash
# =============================================================================
# Cài / cập nhật web Agent tự sửa trên server trolyhoso (Ubuntu/Debian).
#
#   bash setup.sh install   # lần đầu: cài gói, clone repo, venv, Mongo chỉ đọc, compose, systemd
#   bash setup.sh update    # kéo main mới nhất (khi agent rảnh), build lại web + backend thử, restart dịch vụ
#   bash setup.sh check     # kiểm tra mọi thứ đã sống
#
# Chạy bằng user thường có sudo và thuộc nhóm docker (KHÔNG chạy bằng root).
# Script KHÔNG sửa gì trong thư mục production (PROD_DIR): chỉ đọc .env để lấy cổng / Mongo / uploads, và tạo một
# tài khoản Mongo role "read" trong Mongo production.
# =============================================================================
set -euo pipefail

PROD_DIR="${PROD_DIR:-/opt/autofill-hcc}"
REPO_URL="${REPO_URL:-git@github.com:dev-f19/test-auto-test-and-fix.git}"
APP_DIR="${APP_DIR:-$HOME/test-auto-test-and-fix}"
BRANCH="${BRANCH:-main}"
AT="$APP_DIR/auto-test-hcc"
DEPLOY="$AT/deploy"
COMPOSE=(docker compose -f "$DEPLOY/compose.server.yml")
TEST_PORT=12015

say() { printf '\n==> %s\n' "$*"; }
die() { printf '\n[LỖI] %s\n' "$*" >&2; exit 1; }

env_get() {  # env_get <file> <KEY> → giá trị (bỏ ngoặc), rỗng nếu không có
  local line
  line="$(grep -E "^$2=" "$1" 2>/dev/null | tail -n1 || true)"
  line="${line#*=}"; line="${line%\"}"; line="${line#\"}"; line="${line%\'}"; line="${line#\'}"
  printf '%s' "$line"
}

set_kv() {  # set_kv <file> <KEY> <value>: thay dòng KEY=..., chưa có thì thêm
  local file="$1" key="$2" value="$3" tmp
  tmp="$(mktemp)"
  if grep -qE "^$key=" "$file"; then
    awk -v k="$key" -v v="$value" 'BEGIN{FS=OFS="="} $1==k {print k "=" v; next} {print}' "$file" > "$tmp"
  else
    cat "$file" > "$tmp"; printf '%s=%s\n' "$key" "$value" >> "$tmp"
  fi
  cat "$tmp" > "$file"; rm -f "$tmp"
}

agent_busy() {
  curl -s --max-time 3 http://127.0.0.1:12009/agent-api/health | python3 -c \
    'import json,sys; d=json.load(sys.stdin); print("1" if d.get("busy") or d.get("queued") else "")' 2>/dev/null || true
}

preflight() {
  [ "$(id -u)" != "0" ] || die "Đừng chạy bằng root. Tạo user thường (vd autotest), thêm vào nhóm docker và sudo."
  command -v apt-get >/dev/null || die "Script viết cho Ubuntu/Debian (apt-get)."
  [ -f "$PROD_DIR/.env" ] || die "Không thấy $PROD_DIR/.env: đặt PROD_DIR=<thư mục production> rồi chạy lại."
  docker info >/dev/null 2>&1 || die "User $(whoami) chưa gọi được docker (thêm vào nhóm docker rồi đăng nhập lại)."
}

install_packages() {
  say "Cài gói hệ thống (git, python venv, node)"
  sudo apt-get update -y
  sudo apt-get install -y git curl ca-certificates python3 python3-venv python3-pip
  if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get install -y nodejs
  fi
  if ! command -v claude >/dev/null; then
    say "Cài Claude Code"
    curl -fsSL https://claude.ai/install.sh | bash
  fi
}

clone_repo() {
  if [ -d "$APP_DIR/.git" ]; then
    say "Repo đã có ở $APP_DIR"
  else
    say "Clone $REPO_URL → $APP_DIR (cần deploy key có quyền ghi, xem HUONG-DAN-SERVER.md)"
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
  fi
  git -C "$APP_DIR" push --dry-run origin "HEAD:refs/heads/agent/_kiem-tra-quyen" >/dev/null 2>&1 \
    || echo "  [CẢNH BÁO] Chưa push được lên origin: bản sửa đạt sẽ không lên GitHub cho tới khi có deploy key quyền ghi."
}

python_env() {
  say "Tạo venv Python + thư viện backend"
  local py
  py="$(command -v python3.11 || command -v python3.12 || command -v python3)"
  [ -d "$AT/.venv" ] || "$py" -m venv "$AT/.venv"
  PYTHONUTF8=1 "$AT/.venv/bin/pip" install -q --upgrade pip
  PYTHONUTF8=1 "$AT/.venv/bin/pip" install -q -r "$APP_DIR/auto-fill-hcc-backend/requirements.txt" \
    pytest mongomock
}

backend_env() {
  local be_env="$APP_DIR/auto-fill-hcc-backend/.env"
  if [ ! -f "$be_env" ]; then
    say "Chép .env production cho backend thử (compose.server.yml ghi đè Mongo / JWT / vault)"
    install -m 600 "$PROD_DIR/.env" "$be_env"
  fi
}

extension_port() {
  say "Extension của bot trỏ backend thử localhost:$TEST_PORT (chỉ trên server, không commit)"
  local cfg="$APP_DIR/auto-fill-hcc-extension/api/config.js" man="$APP_DIR/auto-fill-hcc-extension/manifest.json"
  git -C "$APP_DIR" update-index --no-skip-worktree auto-fill-hcc-extension/api/config.js auto-fill-hcc-extension/manifest.json
  sed -i -E "s#^const BACKEND_URL = \"[^\"]*\";#const BACKEND_URL = \"http://localhost:$TEST_PORT\";#" "$cfg"
  sed -i -E "s#(https?|wss?)://localhost:12005/#\1://localhost:$TEST_PORT/#g" "$man"
  grep -q "http://localhost:$TEST_PORT\"" "$cfg" || die "Không đổi được BACKEND_URL trong $cfg"
  # Bản sửa của agent không bao giờ đụng 2 file này (codeguard cấm), skip-worktree để git status sạch.
  git -C "$APP_DIR" update-index --skip-worktree auto-fill-hcc-extension/api/config.js auto-fill-hcc-extension/manifest.json
}

mongo_readonly() {
  local server_env="$AT/server.env" pw container root_user root_pw db
  pw="$(env_get "$server_env" AUTOTEST_SOURCE_MONGO_URI | sed -nE 's#^mongodb://autotest_ro:([^@]+)@.*#\1#p')"
  if [ -n "$pw" ] && [ "$pw" != "<mat-khau>" ]; then
    say "Tài khoản Mongo chỉ đọc đã có trong server.env"
    return
  fi
  say "Tạo tài khoản Mongo production CHỈ ĐỌC autotest_ro"
  container="$(docker ps --filter volume=autofill_hcc_mongo_data --format '{{.Names}}' | head -n1)"
  [ -n "$container" ] || die "Không thấy container Mongo production (volume autofill_hcc_mongo_data)."
  root_user="$(env_get "$PROD_DIR/.env" MONGO_USERNAME)"; root_user="${root_user:-root}"
  root_pw="$(env_get "$PROD_DIR/.env" MONGO_PASSWORD)"
  db="$(env_get "$PROD_DIR/.env" MONGO_DB)"; db="${db:-autofill_hcc}"
  pw="$(openssl rand -hex 24)"
  docker exec -i "$container" mongosh --quiet -u "$root_user" -p "$root_pw" --authenticationDatabase admin admin --eval "
    const u = db.getUser('autotest_ro');
    if (u) db.updateUser('autotest_ro', {pwd: '$pw', roles: [{role: 'read', db: '$db'}]});
    else db.createUser({user: 'autotest_ro', pwd: '$pw', roles: [{role: 'read', db: '$db'}]});
  " >/dev/null
  set_kv "$server_env" AUTOTEST_SOURCE_MONGO_URI "mongodb://autotest_ro:$pw@127.0.0.1:12004/?authSource=admin"
  set_kv "$server_env" AUTOTEST_SOURCE_DB "$db"
}

server_env() {
  local server_env="$AT/server.env" prod_port storage
  if [ ! -f "$server_env" ]; then
    install -m 600 "$DEPLOY/server.env.example" "$server_env"
  fi
  prod_port="$(env_get "$PROD_DIR/.env" PORT)"; prod_port="${prod_port:-8000}"
  storage="$(env_get "$PROD_DIR/.env" STORAGE_DIR)"; storage="${storage:-data/uploads}"
  storage="${storage#./}"; storage="${storage#/app/}"
  set_kv "$server_env" AUTOTEST_SOURCE_UPLOADS "$PROD_DIR/$storage"
  set_kv "$server_env" AUTOTEST_DENY_READ_DIRS "$PROD_DIR"
  set_kv "$server_env" AUTOTEST_AUTH_BACKEND "http://127.0.0.1:$prod_port"
  set_kv "$server_env" AUTOTEST_COMPOSE_FILE "$DEPLOY/compose.server.yml"
  set_kv "$server_env" AUTOTEST_TEST_DB "$(env_get "$PROD_DIR/.env" MONGO_DB || true)"
  [ -n "$(env_get "$server_env" AUTOTEST_TEST_DB)" ] || set_kv "$server_env" AUTOTEST_TEST_DB autofill_hcc
  mongo_readonly
  [ -r "$PROD_DIR/$storage" ] || echo "  [CẢNH BÁO] User $(whoami) chưa đọc được $PROD_DIR/$storage: cấp quyền đọc (vd setfacl -R -m u:$(whoami):rX)."

  local compose_env="$DEPLOY/.env"
  [ -f "$compose_env" ] || install -m 600 /dev/null "$compose_env"
  set_kv "$compose_env" AUTH_BACKEND_URL "http://127.0.0.1:$prod_port"
  [ -n "$(env_get "$compose_env" TEST_JWT_ACCESS_SECRET)" ] || set_kv "$compose_env" TEST_JWT_ACCESS_SECRET "$(openssl rand -hex 32)"
  [ -n "$(env_get "$compose_env" TEST_JWT_REFRESH_SECRET)" ] || set_kv "$compose_env" TEST_JWT_REFRESH_SECRET "$(openssl rand -hex 32)"
}

systemd_units() {
  say "Cài systemd: autotest-agent (dịch vụ agent)"
  local user
  user="$(whoami)"
  for unit in autotest-agent; do
    sed -e "s#__USER__#$user#g" -e "s#__APP_DIR__#$APP_DIR#g" "$DEPLOY/$unit.service" \
      | sudo tee "/etc/systemd/system/$unit.service" >/dev/null
  done
  sudo systemctl daemon-reload
  sudo systemctl enable autotest-agent >/dev/null
}

compose_up() {
  say "Build + bật web 12008, backend thử 12015, Mongo thử 12014"
  "${COMPOSE[@]}" up -d --build
}

restart_services() {
  sudo systemctl restart autotest-agent
}

check() {
  say "Kiểm tra"
  local ok=1
  curl -s --max-time 5 "http://127.0.0.1:$TEST_PORT/healthz" | grep -q '"ok":true' \
    && echo "  backend thử 12015: sống" || { echo "  backend thử 12015: CHƯA sống"; ok=0; }
  curl -s --max-time 5 http://127.0.0.1:12009/agent-api/health | grep -q '"claude":true' \
    && echo "  dịch vụ agent 12009: sống, có claude" || { echo "  dịch vụ agent 12009: CHƯA sống hoặc chưa có claude (journalctl -u autotest-agent)"; ok=0; }
  curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:12008/ | grep -q 200 \
    && echo "  web 12008: sống" || { echo "  web 12008: CHƯA sống"; ok=0; }
  [ -n "$(env_get "$AT/server.env" CLAUDE_CODE_OAUTH_TOKEN)" ] \
    || echo "  [CẦN LÀM] Chưa có CLAUDE_CODE_OAUTH_TOKEN trong $AT/server.env: chạy 'claude setup-token', dán token, rồi 'sudo systemctl restart autotest-agent'."
  [ "$ok" = 1 ] && echo "  Tất cả đã sống." || return 1
}

case "${1:-}" in
  install)
    preflight
    install_packages
    clone_repo
    python_env
    backend_env
    extension_port
    server_env
    systemd_units
    compose_up
    restart_services
    sleep 5
    check || true
    ;;
  update)
    preflight
    [ -z "$(agent_busy)" ] || die "Agent đang chạy hoặc còn ca trong hàng đợi: đợi xong hẵng cập nhật."
    say "Kéo $BRANCH mới nhất"
    git -C "$APP_DIR" update-index --no-skip-worktree auto-fill-hcc-extension/api/config.js auto-fill-hcc-extension/manifest.json
    git -C "$APP_DIR" checkout -- auto-fill-hcc-extension/api/config.js auto-fill-hcc-extension/manifest.json
    git -C "$APP_DIR" pull --ff-only origin "$BRANCH" \
      || die "Không kéo được (thư mục làm việc còn bản sửa chưa gộp?). Xem 'git -C $APP_DIR status'."
    extension_port
    PYTHONUTF8=1 "$AT/.venv/bin/pip" install -q -r "$APP_DIR/auto-fill-hcc-backend/requirements.txt"
    systemd_units
    compose_up
    restart_services
    sleep 5
    check || true
    ;;
  check)
    check
    ;;
  *)
    echo "Dùng: bash setup.sh install | update | check"; exit 1
    ;;
esac
