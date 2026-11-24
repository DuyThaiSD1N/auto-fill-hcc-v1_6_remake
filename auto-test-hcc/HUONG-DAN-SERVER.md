# Chạy Auto test + Agent tự sửa với req production

Có hai cách. Ngày 17/11/2026 người dùng chốt dùng **cách A**. Ngày 23/11/2026 người dùng quyết định đưa lên production theo **cách B**: Auto test cùng Agent tự sửa nằm trong Monitor, cài từ repo backend nhánh `auto-fix`.

- **A. Máy local đọc req từ server qua SSH.** Web, agent, Claude và backend thử (Docker local 12025, build từ khu làm việc) đều nằm trên máy local.
  Server chỉ cần một khoá SSH bị giới hạn và một tài khoản Mongo chỉ đọc. Không cài gì, không deploy gì lên server.
- **B. Cài cả hệ thống lên server production.** Xem mục B.

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

Mọi thứ khác như máy local: backend thử là Docker local 12025 (khu làm việc, tag release đang chạy production), đăng nhập web 12008 bằng super_admin **local**. Lượt chạy lại
dùng tài khoản test dịch vụ tự dựng trên Mongo local, cùng username, xã, tỉnh với tài khoản đã điền req trên production (`replay.shadow_account`, cờ `autotest_shadow`); trùng tài khoản test có sẵn của người khác thì dùng tên `autotest-<username>`. Dịch vụ tự mở đường hầm `127.0.0.1:12024 → Mongo server` và tải tệp gốc qua
`read-uploads.sh` khi cần. Bật lại dịch vụ: `python auto-test-hcc/agents/server.py`.

- Tệp gốc của req được tải về `auto-test-hcc/runs/` trên máy local (gitignore). Đó là giấy tờ thật của người dân.
- **Chỉ chạy được req vừa điền, trong khoảng 30 phút.** Worker `archive` của backend production gửi mỗi lượt sang kho lưu trữ (vault),
  rồi khoảng `ARCHIVE_AFTER_MINUTES` (mặc định 30) phút sau lượt cuối thì xoá tệp gốc khỏi đĩa và xoá `fields`, `options`, OCR, câu trả
  lời LLM khỏi Mongo. Kiểm ngày 17/11/2026: 3.943 req trong 24 giờ, không req nào còn `fields`. Req đã archive thì web báo "đã được
  backend chuyển sang kho lưu trữ". Cách dùng: tester điền xong thấy lỗi thì tạo ca ngay; dịch vụ chép chứng cứ về máy lúc tạo ca nên
  các bước sau không bị ảnh hưởng. Req cũ hơn: khai kho lưu trữ "Quản lý nội bộ" trong `server.env` (`AUTOTEST_ARCHIVE_URL`, `AUTOTEST_ARCHIVE_USER`, `AUTOTEST_ARCHIVE_PASSWORD`, tài khoản viewer) thì dịch vụ tự lấy req đã archive từ kho, không giới hạn thời gian.
- Có `server.env` này thì mọi mã req đều tra trên trolysoao, không tra Mongo local nữa. Muốn quay lại req local thì đổi tên tệp rồi bật lại dịch vụ.
- Gỡ quyền: xoá dòng `autotest` trong `~/.ssh/authorized_keys` trên server và chạy `db.dropUser('autotest_ro')`.

**A4. Vào web bằng IP Tailscale của server (`http://<ip-trolysoao>:12008`).** Web vẫn chạy trên máy local; máy local không có quyền
admin để mở firewall cho máy khác gọi vào, nên đi đường ngược:

1. Máy local: thêm `AUTOTEST_PUBLISH_WEB=12018:127.0.0.1:12008` vào `server.env`. Dịch vụ agent tự giữ `ssh -R` bằng khoá
   `autotest_trolysoao`, đưa web 12008 lên `127.0.0.1:12018` trên server, rớt thì tự nối lại (`/agent-api/health` có `"publish": true`).
2. Server (chạy một lần): container chỉ nghe trên IP Tailscale, tự lên lại khi server khởi động lại:

   ```bash
   docker run -d --name autotest-web-proxy --restart unless-stopped --network host alpine/socat:latest \
     TCP-LISTEN:12008,bind=<ip-trolysoao>,fork,reuseaddr TCP:127.0.0.1:12018
   ```
3. Nên siết khoá: dòng `port-forwarding` hiện cho khoá mở đường hầm ngược tới mọi cổng loopback của server. Thêm `permitlisten` để
   chỉ còn đúng cổng 12018:

   ```bash
   cp ~/.ssh/authorized_keys ~/.ssh/authorized_keys.bak-autotest-listen
   sed -i '/read-uploads.sh/ s/permitopen="127.0.0.1:12004",/permitopen="127.0.0.1:12004",permitlisten="127.0.0.1:12018",/' ~/.ssh/authorized_keys
   ```

Máy local tắt hoặc dịch vụ agent dừng thì địa chỉ này trả lỗi. Gỡ: `docker rm -f autotest-web-proxy` và bỏ dòng trong `server.env`.

---

## B. Cài Auto test + Agent tự sửa lên server production (từ repo backend, nhánh `auto-fix`)

Tài liệu cho người cài đặt. Cài trên máy đang chạy backend production (thư mục production, gọi là `PROD_DIR`, ví dụ `/opt/autofill-hcc`). Hệ thống chỉ ĐỌC req thật của production. Mọi bản sửa đều build và chạy thử trên một backend riêng. Backend production không bị build lại, cũng không bị đổi code.

Người dùng vào từ **Monitor production** (cổng 12007), nhóm menu **Auto test**: Agent tự sửa, Tái hiện lượt, Nội dung đã điền, Bộ ca test, Lần chạy, Cấu hình ghi. Web 12008 vẫn chạy, vừa dùng riêng được, vừa là cầu nối để Monitor gọi được dịch vụ agent.

### Sơ đồ

| Thành phần | Cổng | Chạy ở đâu | Việc |
| --- | --- | --- | --- |
| Monitor production (`monitor-fe`) | 12007 | Stack production (`compose.prod.yml`) | Nhóm menu Auto test; `/agent-api/` đi tới `AGENT_URL` |
| Web Agent tự sửa (`test-fe`) | 12008 | Docker, mạng host | Giao diện riêng + cầu nối `/agent-api/` → `127.0.0.1:12009` |
| Dịch vụ agent | 127.0.0.1:12009 | systemd `autotest-agent` | Hội đồng agent, lab, chạy test, build backend thử, đẩy nhánh lên GitHub |
| Backend thử (`autotest-app`) | 127.0.0.1:12015 | Docker, `deploy/compose.server.yml` | Chạy code agent đang sửa; chạy lại 5 lần trên đây |
| Mongo thử (`be-mongo`) | 127.0.0.1:12014 | Docker | Dữ liệu và tài khoản test của backend thử |
| Mongo production | 127.0.0.1:12004 | Stack production | Dịch vụ chỉ ĐỌC req (tài khoản `autotest_ro`, role `read`) |
| Uploads production | `PROD_DIR/data/uploads` | Đĩa | Dịch vụ chỉ đọc tệp gốc của req |
| Kho lưu trữ | (đơn vị cấp) | Ngoài server | Đọc req đã bị archive (~30 phút sau lượt cuối), tài khoản dịch vụ chỉ đọc |

Bản clone `~/autotest-hcc` (repo `dev-f19/auto-fill-hcc-backend`, nhánh `auto-fix`) chỉ chứa code của dịch vụ. Agent **không sửa** bản clone này. Mỗi ca, agent sửa trong khu làm việc `~/.autotest-hcc/workspace`: clone riêng 3 repo thật (backend, Auto Fill, trợ lý), đặt đúng tag release đang chạy production. Bản sửa được duyệt và chạy lại đạt sẽ thành nhánh `agent/<mã ca>` trên đúng repo bị sửa, kèm link mở PR. `main` không bị đụng.

### Các chốt an toàn

- Dịch vụ từ chối khởi động nếu cấu hình có thể đụng vào production: build bằng `compose.prod.yml` hoặc `compose.local.yml`, Mongo thử trùng Mongo production, backend thử trùng backend production, cài từ repo backend mà tắt khu làm việc.
- Backend thử dùng image `autofill-hcc-be:autotest`, project compose riêng, service tên `autotest-app` (không trùng `app` của production), volume riêng, JWT secret riêng, tắt vault form snapshot.
- Agent không có Bash. Agent bị chặn Read `PROD_DIR/**` (`.env` production, uploads của mọi người dân), `server.env`, `~/.ssh`, và bản clone `~/autotest-hcc` (có bản chép `.env` production).
- Bot không nộp hồ sơ, không mở cổng, không chạy Chromium (từ 18/11/2026): mọi lần chạy lại gọi backend thử.
- Mọi thao tác ở lab (mở lượt, tải gói ghi thô, tạo ca) đều ghi nhật ký ở `auto-test-hcc/runs/_lab/access.jsonl`, xem ở màn Cấu hình ghi.
- `auto-test-hcc/` nằm trong `.dockerignore` của backend: `runs/` chứa giấy tờ thật, không được vào image.

**Lưu ý dữ liệu:** req lấy từ production là hồ sơ thật của người dân. Mỗi ca, agent gửi OCR và ảnh giấy tờ của req đó lên Anthropic qua tài khoản Claude cắm vào server. Đơn vị phải cho phép việc này trước khi dùng.

### B1. Chuẩn bị (làm một lần, có quyền sudo)

```bash
# User riêng cho dịch vụ, KHÔNG dùng root
sudo adduser autotest
sudo usermod -aG docker,sudo autotest
# Cho đọc tệp gốc của req (chỉ đọc)
sudo apt-get install -y acl
sudo setfacl -R -m u:autotest:rX <PROD_DIR>/data/uploads
sudo setfacl -R -d -m u:autotest:rX <PROD_DIR>/data/uploads
sudo setfacl -m u:autotest:r <PROD_DIR>/.env
```

Quyền GitHub cho user `autotest`: đọc repo `dev-f19/auto-fill-hcc-backend` để clone nhánh `auto-fix`, và đọc + push 3 repo thật
(`auto-fill-hcc-backend`, `auto-fill-hcc-extension`, `tro-ly-nguoi-dan-extension`) để khu làm việc clone tag release và đẩy nhánh
`agent/<mã ca>`. Cách đơn giản: một token GitHub (fine-grained, 3 repo, quyền Contents read/write) lưu bằng
`git config --global credential.helper store`. Dùng deploy key thì mỗi repo một khoá, đặt `AUTOTEST_*_GIT_URL` sang URL ssh trong `server.env`.

### B2. Cài đặt

```bash
sudo -iu autotest
PROD_DIR=<PROD_DIR> bash -c 'git clone --branch auto-fix git@github.com:dev-f19/auto-fill-hcc-backend.git ~/autotest-hcc \
  && bash ~/autotest-hcc/auto-test-hcc/deploy/setup.sh install'
```

Script lần lượt:

1. Cài gói hệ thống, Node 22, Claude Code.
2. Tạo venv Python, cài thư viện backend (để chạy test và bộ ca test).
3. Chép `.env` production cho backend thử.
4. Tạo tài khoản Mongo chỉ đọc và sinh `auto-test-hcc/server.env` (bật khu làm việc).
5. Build và bật compose (web 12008, backend thử 12015, Mongo thử 12014), cài và bật dịch vụ systemd `autotest-agent`.
6. Chạy kiểm tra, in các việc còn thiếu.

### B3. Cắm tài khoản Claude và tài khoản kho lưu trữ

```bash
claude setup-token          # đăng nhập tài khoản Claude của bạn, in ra token
nano ~/autotest-hcc/auto-test-hcc/server.env
#   CLAUDE_CODE_OAUTH_TOKEN=<token>
#   AUTOTEST_ARCHIVE_URL=<địa chỉ kho>   AUTOTEST_ARCHIVE_USER=<tài khoản dịch vụ>   AUTOTEST_ARCHIVE_PASSWORD=<mật khẩu>
sudo systemctl restart autotest-agent
bash ~/autotest-hcc/auto-test-hcc/deploy/setup.sh check
```

Tài khoản kho là **tài khoản dịch vụ riêng do đơn vị cấp**, chỉ đọc. Không dùng tài khoản cá nhân. Thiếu tài khoản này thì chỉ mở được những lượt còn trong Mongo production (chưa bị archive).

Chi phí agent tính vào tài khoản Claude này. Một ca thường tốn 2 đến 6 USD theo giá niêm yết, trần 30 USD.

### B4. Nối Monitor production với dịch vụ agent

Monitor build từ nhánh có thư mục `monitor-fe/src/autotest/` (nhánh `auto-fix` sau khi gộp vào `main` và phát hành tag). Dịch vụ agent chỉ nghe `127.0.0.1:12009`, container Monitor không gọi được loopback của máy host, nên Monitor đi qua web 12008 (mạng host):

1. Trong `compose.prod.yml` của server, service `monitor-fe` phải có `AGENT_URL=${AGENT_URL:-...}` và `extra_hosts: ["host.docker.internal:host-gateway"]` (bản trong repo đã có).
2. Thêm vào `<PROD_DIR>/.env`: `AGENT_URL=http://host.docker.internal:12008`
3. Tạo lại Monitor: `cd <PROD_DIR> && docker compose -f compose.prod.yml up -d monitor-fe`
4. Kiểm tra: `curl -s http://127.0.0.1:12007/agent-api/health` phải ra JSON có `"lab": true`. Tải lại Monitor là thấy nhóm menu Auto test.

Lúc khởi động, Monitor tự đổi `host.docker.internal` thành IP ghi trong `/etc/hosts` (`monitor-fe/docker-entrypoint.d/18-agent-url.envsh`), vì resolver DNS của Docker mà nginx dùng không đọc `extra_hosts`. Server có bật firewall (ufw) thì phải cho mạng Docker vào cổng 12008, ví dụ `sudo ufw allow from 172.16.0.0/12 to any port 12008 proto tcp`.

Dịch vụ agent tắt thì `/agent-api/` trả 502 và Monitor tự ẩn nhóm menu Auto test. Các màn khác của Monitor không bị ảnh hưởng.

### B5. Tài khoản test trên backend thử

Khi tạo ca, dịch vụ tự dựng tài khoản chạy lại cùng tỉnh, xã với req trên backend thử (`replay.shadow_account`). Không cần tạo tay. Đăng nhập Monitor / web 12008 bằng tài khoản super_admin của **production**.

### B6. Mở web ra ngoài

Monitor 12007 và web 12008 đọc được hồ sơ thật. Chỉ mở cho mạng nội bộ hoặc VPN, hoặc đặt sau reverse proxy HTTPS đang dùng. Đừng mở thẳng ra Internet.

### B7. Chạy một ca

1. Monitor › Auto test › **Agent tự sửa** › Tạo ca mới: nhập mã req của production và mô tả lỗi. Hoặc mở một lượt ở **Tái hiện lượt** rồi bấm **Gửi Agent tự sửa**, mã req được điền sẵn.
2. Duyệt kế hoạch, rồi duyệt patch. Đạt thì trang ca hiện nhánh `agent/<mã ca>` của từng repo bị sửa, kèm link mở PR.
3. **Bộ ca test**: tạo ca từ lượt thật (ẩn danh) ở Tái hiện lượt, chạy trên bản production (tag release, khu làm việc) hoặc bản nhánh đang cài.

### B8. Cập nhật code mới

Khi agent đang rảnh:

```bash
bash ~/autotest-hcc/auto-test-hcc/deploy/setup.sh update
```

Lệnh này kéo nhánh `auto-fix` mới nhất (đổi bằng `BRANCH=main` khi đã gộp), cài lại thư viện, build lại web và backend thử, restart dịch vụ. Bản sửa của agent nằm trong khu làm việc nên không chặn lệnh kéo. Phần Monitor cập nhật theo đường phát hành bình thường của backend (tag `v20*`).

### B9. Lỗi hay gặp

| Hiện tượng | Xử lý |
| --- | --- |
| `autotest-agent` không lên, log ghi "Không khởi động: cấu hình server…" | Sửa đúng biến mà log nêu trong `server.env` (`journalctl -u autotest-agent`) |
| Monitor không có nhóm menu Auto test | `curl http://127.0.0.1:12007/agent-api/health`: 502 là thiếu `AGENT_URL` (mục B4), dịch vụ tắt, hoặc firewall chặn 12008 |
| Web báo "Không thấy req trong Mongo nguồn, kho lưu trữ…" | Req đã bị archive mà chưa có tài khoản kho (mục B3); hoặc sai `AUTOTEST_SOURCE_MONGO_URI` / `AUTOTEST_SOURCE_DB` |
| "Tệp gốc của req không còn trên đĩa" | User `autotest` chưa đọc được uploads: chạy lại lệnh `setfacl` ở mục B1 |
| Khu làm việc không clone / không push được | Thiếu quyền GitHub của user `autotest` (mục B1); thử `git ls-remote https://github.com/dev-f19/auto-fill-hcc-extension.git` |
| Bộ ca test báo "Không có cây backend này" | Bản production dùng khu làm việc, khu này chỉ được clone khi bắt đầu một ca: chạy một ca Agent tự sửa trước |

### Cài từ bản clone monorepo cũ (`dev-f19/test-auto-test-and-fix`)

Vẫn chạy được: `REPO_URL=git@github.com:dev-f19/test-auto-test-and-fix.git APP_DIR=~/test-auto-test-and-fix BRANCH=main bash setup.sh install`. Ở bố cục này, mặc định agent sửa thẳng bản clone (không khu làm việc), bản sửa đạt đẩy lên `AUTOTEST_GIT_REMOTE`.
