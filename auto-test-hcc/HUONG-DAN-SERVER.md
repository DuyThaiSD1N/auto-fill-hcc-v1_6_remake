# Chạy web Agent tự sửa với req của trolysoao

Có hai cách. Người dùng chốt ngày 17/11/2026 dùng **cách A**.

- **A. Máy local đọc req từ server qua SSH.** Web, agent, Claude, cửa sổ bot và backend thử (Docker local 12025, build từ khu làm việc) đều nằm trên máy local.
  Server chỉ cần một khoá SSH bị giới hạn và một tài khoản Mongo chỉ đọc. Không cài gì, không deploy gì lên server.
- **B. Cài cả hệ thống lên server.** Xem từ mục "Sơ đồ" trở xuống.

## A. Đọc req trolysoao từ máy local

Server trolysoao: `nlp@<ip-trolysoao>` (IP Tailscale, hỏi người phụ trách; không ghi IP vào repo), production ở `/home/nlp/hcc` (app 12005, Mongo `127.0.0.1:12004`, container `hcc-mongo-1`).

**A1. Trên máy local (PowerShell), tạo khoá riêng:**

```powershell
ssh-keygen -t ed25519 -N '""' -C "auto-test-hcc local" -f $HOME\.ssh\autotest_trolysoao
Get-Content $HOME\.ssh\autotest_trolysoao.pub
scp auto-test-hcc/deploy/read-uploads.sh nlp@<ip-trolysoao>:/tmp/read-uploads.sh
```

**A2. Trên server (`ssh nlp@<ip-trolysoao>`):**

```bash
mkdir -p ~/.autotest && install -m 755 /tmp/read-uploads.sh ~/.autotest/read-uploads.sh
cp ~/.ssh/authorized_keys ~/.ssh/authorized_keys.bak-autotest
# Thay <PUB> bằng dòng in ra ở A1. Khoá này chỉ mở được đường hầm tới Mongo và đọc uploads, không có shell.
echo 'restrict,port-forwarding,permitopen="127.0.0.1:12004",command="/home/nlp/.autotest/read-uploads.sh" <PUB>' >> ~/.ssh/authorized_keys

# Tài khoản Mongo CHỈ ĐỌC. Ghi lại mật khẩu in ra.
cd /home/nlp/hcc
U=$(grep -E '^MONGO_USERNAME=' .env | cut -d= -f2- | tr -d "\"'"); P=$(grep -E '^MONGO_PASSWORD=' .env | cut -d= -f2- | tr -d "\"'")
RO=$(openssl rand -hex 24); echo "Mật khẩu autotest_ro: $RO"
docker exec -i hcc-mongo-1 mongosh --quiet -u "${U:-root}" -p "$P" --authenticationDatabase admin admin \
  --eval "db.createUser({user:'autotest_ro',pwd:'$RO',roles:[{role:'read',db:'autofill_hcc'}]})"
```

**A3. Trên máy local, tạo `auto-test-hcc/server.env` (gitignore):**

```ini
AUTOTEST_SOURCE_SSH=nlp@<ip-trolysoao>
AUTOTEST_SOURCE_SSH_KEY=C:/Users/<ten-may>/.ssh/autotest_trolysoao
AUTOTEST_SOURCE_TUNNEL=12024:127.0.0.1:12004
AUTOTEST_SOURCE_MONGO_URI=mongodb://autotest_ro:<mat-khau-A2>@127.0.0.1:12024/?authSource=admin&directConnection=true
AUTOTEST_SOURCE_DB=autofill_hcc
# Tuỳ chọn: bản sửa đạt lên nhánh agent/<mã ca> của repo test (dùng quyền git của máy này)
AUTOTEST_GIT_REMOTE=https://github.com/dev-f19/test-auto-test-and-fix.git
```

Mọi thứ khác như máy local: backend thử là Docker local 12025 (khu làm việc, tag release đang chạy production), đăng nhập web 12008 bằng super_admin **local**, chạy lại bằng
tài khoản test local đúng tỉnh và xã của req. Dịch vụ tự mở đường hầm `127.0.0.1:12024 → Mongo server` và tải tệp gốc qua
`read-uploads.sh` khi cần. Bật lại dịch vụ: `python auto-test-hcc/agents/server.py`.

- Tệp gốc của req được tải về `auto-test-hcc/runs/` trên máy local (gitignore). Đó là giấy tờ thật của người dân.
- Uploads trên server chỉ giữ vài ngày gần nhất: req cũ hơn sẽ báo "Tệp gốc của req không còn trên đĩa".
- Gỡ quyền: xoá dòng `autotest` trong `~/.ssh/authorized_keys` trên server và chạy `db.dropUser('autotest_ro')`.

---

Từ đây trở xuống là **cách B**: cài cả hệ thống lên server.

Tài liệu cho người cài đặt. Cài trên máy đang chạy backend production (`/opt/autofill-hcc`). Hệ thống lấy req thật từ production, nhưng mọi bản sửa đều build và chạy thử trên một backend riêng. Backend production không bị build lại hay đổi code.

## Sơ đồ

| Thành phần | Cổng | Chạy ở đâu | Việc |
| --- | --- | --- | --- |
| Web Agent tự sửa (`test-fe`) | 12008 | Docker, mạng host | Giao diện; `/auth/` đi tới backend production để đăng nhập super_admin; `/vnc/` mở màn hình bot (cần vé) |
| Dịch vụ agent | 127.0.0.1:12009 | systemd `autotest-agent` | Hội đồng agent, chạy test, build backend thử, đẩy nhánh lên GitHub |
| Backend thử (`app`) | 127.0.0.1:12015 | Docker, `deploy/compose.server.yml` | Chạy code agent đang sửa; chạy lại 5 lần trên đây |
| Mongo thử (`be-mongo`) | 127.0.0.1:12014 | Docker | Dữ liệu và tài khoản test của backend thử |
| Màn hình ảo + noVNC | 127.0.0.1:6080 | systemd `autotest-vnc` | Cửa sổ Chromium của bot, bạn đăng nhập VNeID qua web |
| Mongo production | 127.0.0.1:12004 | Stack production | Dịch vụ chỉ ĐỌC req (tài khoản `autotest_ro`, role `read`) |
| Uploads production | `/opt/autofill-hcc/data/uploads` | Đĩa | Dịch vụ chỉ đọc tệp gốc của req |

Code được sửa nằm trong bản clone `~/test-auto-test-and-fix` của repo `dev-f19/test-auto-test-and-fix`. Bản sửa được duyệt và chạy lại đạt sẽ thành một commit trên nhánh `agent/<mã ca>`, push lên GitHub. `main` không bị đụng, ai muốn gộp thì mở PR.

## Các chốt an toàn

- Dịch vụ từ chối khởi động nếu cấu hình server có thể đụng vào production: build bằng `compose.prod.yml`, Mongo thử trùng Mongo production, backend thử trùng backend production.
- Backend thử dùng image `autofill-hcc-be:autotest`, project compose riêng, volume riêng, JWT secret riêng, tắt vault form snapshot.
- Agent không có Bash. Ngoài các luật cũ, agent còn bị chặn Read `/opt/autofill-hcc/**` (`.env` production, uploads của mọi người dân), `server.env`, `~/.ssh`.
- Bot không nộp hồ sơ: lớp chặn nộp trong `agents/browser.py` giữ nguyên.

**Lưu ý dữ liệu:** req lấy từ production là hồ sơ thật của người dân. Mỗi ca, agent gửi OCR và ảnh giấy tờ của req đó lên Anthropic qua tài khoản Claude cắm vào server. Đơn vị phải cho phép việc này trước khi dùng.

## 1. Chuẩn bị (làm một lần, có quyền sudo)

```bash
# User riêng cho dịch vụ, KHÔNG dùng root (Chromium của bot cần sandbox)
sudo adduser autotest
sudo usermod -aG docker,sudo autotest
# Cho đọc tệp gốc của req (chỉ đọc)
sudo apt-get install -y acl
sudo setfacl -R -m u:autotest:rX /opt/autofill-hcc/data/uploads
sudo setfacl -R -d -m u:autotest:rX /opt/autofill-hcc/data/uploads
sudo setfacl -m u:autotest:r /opt/autofill-hcc/.env
```

Deploy key để server push được nhánh lên GitHub:

```bash
sudo -iu autotest
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "auto-test-hcc server"
cat ~/.ssh/id_ed25519.pub
```

Dán khoá vào GitHub: repo `dev-f19/test-auto-test-and-fix`, mục Settings, Deploy keys, Add deploy key, tích **Allow write access**.

## 2. Cài đặt

```bash
sudo -iu autotest
git clone git@github.com:dev-f19/test-auto-test-and-fix.git ~/test-auto-test-and-fix
bash ~/test-auto-test-and-fix/auto-test-hcc/deploy/setup.sh install
```

Production nằm ở thư mục khác thì thêm `PROD_DIR=/duong/dan` trước lệnh. Script lần lượt:

1. Cài gói hệ thống, Node 22, Claude Code.
2. Tạo venv và Chromium cho Playwright.
3. Chép `.env` production cho backend thử.
4. Đổi extension của bot sang `localhost:12015`, chỉ trên server, không commit.
5. Tạo tài khoản Mongo chỉ đọc và sinh `auto-test-hcc/server.env`.
6. Build và bật compose, cài và bật hai dịch vụ systemd.
7. Chạy kiểm tra.

## 3. Cắm tài khoản Claude của bạn

```bash
claude setup-token          # đăng nhập tài khoản Claude của bạn, in ra token
nano ~/test-auto-test-and-fix/auto-test-hcc/server.env   # dán vào CLAUDE_CODE_OAUTH_TOKEN=
sudo systemctl restart autotest-agent
bash ~/test-auto-test-and-fix/auto-test-hcc/deploy/setup.sh check
```

Chi phí agent tính vào tài khoản này. Một ca thường tốn 2 đến 6 USD theo giá niêm yết, trần 30 USD.

## 4. Tạo tài khoản test trên backend thử

Mongo thử trống. Mỗi đơn vị cần chạy lại phải có một tài khoản test đúng tỉnh và xã của req:

```bash
cd ~/test-auto-test-and-fix/auto-test-hcc/deploy
docker compose -f compose.server.yml exec app python -m scripts.seed_user \
  --username <ten-test> --password "<mat-khau>" --name "<ten hien thi>" --tinh "Tỉnh ..." --xa "Xã ..."
```

Đăng nhập web 12008 bằng tài khoản super_admin của **production**. Khi tạo ca, ô "tài khoản chạy lại" là tài khoản test vừa tạo trên backend thử.

## 5. Mở web ra ngoài

Web nghe cổng 12008 trên mọi giao diện mạng. Chỉ mở cho mạng nội bộ hoặc VPN, hoặc đặt sau reverse proxy HTTPS đang dùng cho trolyhoso. Đừng mở 12008 thẳng ra Internet: web này đọc được hồ sơ thật.

## 6. Chạy một ca

1. Mở web, đăng nhập super_admin, nhập mã req của production và mô tả lỗi.
2. Khi khung vàng "Đang chờ bạn" hiện lên, bấm **Mở màn hình bot**. Tab noVNC mở ra cửa sổ Chromium trên server. Đăng nhập VNeID ở đó rồi quay lại web bấm nút trong khung vàng.
3. Duyệt patch như ở máy local. Đạt thì web hiện tên nhánh `agent/<mã ca>` trên GitHub.

## 7. Cập nhật code mới

Khi agent đang rảnh:

```bash
bash ~/test-auto-test-and-fix/auto-test-hcc/deploy/setup.sh update
```

Lệnh này kéo `main` mới nhất, build lại web và backend thử, restart dịch vụ. Nếu thư mục làm việc còn bản sửa của ca trước mà chưa ai gộp, lệnh kéo có thể từ chối. Khi đó bấm **Hoàn tác bản sửa** trên web, vì bản sửa đã nằm trên nhánh GitHub, rồi chạy lại lệnh.

## 8. Lỗi hay gặp

| Hiện tượng | Xử lý |
| --- | --- |
| `autotest-agent` không lên, log ghi "Không khởi động: cấu hình server…" | Sửa đúng biến mà log nêu trong `server.env` |
| Web báo "Không thấy req trong Mongo nguồn" | Kiểm tra `AUTOTEST_SOURCE_MONGO_URI` và `AUTOTEST_SOURCE_DB`; chạy lại `setup.sh install` để tạo lại tài khoản chỉ đọc |
| "Tệp gốc của req không còn trên đĩa" | User `autotest` chưa đọc được uploads: chạy lại lệnh `setfacl` ở mục 1 |
| Không push được nhánh | Deploy key chưa tích Allow write access; thử `git -C ~/test-auto-test-and-fix push --dry-run origin HEAD:refs/heads/agent/thu` |
| Nút Mở màn hình bot báo 404 | `AUTOTEST_VNC=1` chưa có trong `server.env` |
| Tab noVNC trắng hoặc báo 502 | `sudo systemctl status autotest-vnc` |
| Xem log | `journalctl -u autotest-agent -f`, `docker compose -f deploy/compose.server.yml logs -f app` |
