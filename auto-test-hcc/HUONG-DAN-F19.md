# Cài web Agent tự sửa cho team F19

Làm theo tài liệu này để dựng hệ thống trên máy của team, dùng đúng file `.env` đang chạy, rồi chạy được ca đầu tiên. Web làm gì và cần kiểm tra gì thì đọc [KE-HOACH.md](KE-HOACH.md).

**Repo này public, ai cũng đọc được.** `.env`, mật khẩu, mã req và giấy tờ không được đưa vào code, tài liệu, issue hay pull request.

## 1. Chuẩn bị

| Cần có | Ghi chú |
| --- | --- |
| Windows, Docker Desktop, Git | Các lệnh dưới đây chạy trong PowerShell |
| Python 3.11, Node 22 | Dịch vụ agent chạy trực tiếp trên máy, không nằm trong Docker |
| Claude Code đã đăng nhập | Chi phí agent tính vào tài khoản này, xem mục 9 |
| Tailscale, cùng mạng với máy OCR và LLM | Thiếu mạng này thì OCR và LLM không chạy. Xin người phụ trách mời vào |
| File `.env` | Xin người phụ trách, xem bước 2 |
| Tài khoản VNeID của người chạy | Dùng để đăng nhập cổng thật |

## 2. Lấy code và `.env`

```powershell
git clone https://github.com/DuyThaiSD1N/auto-fill-hcc-v1_6_remake.git
cd auto-fill-hcc-v1_6_remake
git checkout web-kiem-thu
```

`.env` không có trong repo. Người phụ trách gửi riêng cho từng người, không qua nhóm chat chung. Lưu đúng vào `auto-fill-hcc-backend/.env` và giữ nguyên nội dung. File đã bị git bỏ qua, đừng dùng `git add -f` với nó.

## 3. Cài thư viện Python

```powershell
$env:PYTHONUTF8="1"
pip install -r auto-fill-hcc-backend/requirements.txt playwright
python -m playwright install chromium
```

Thiếu dòng `PYTHONUTF8` thì `pip` báo `UnicodeDecodeError`, vì `requirements.txt` có chú thích tiếng Việt.

## 4. Bật backend và web

```powershell
cd auto-fill-hcc-backend
docker compose -f compose.prod.yml up -d --build
curl.exe -s http://localhost:12005/healthz

# Cho web Monitor đọc Mongo trên máy này, không sửa .env
$env:BACKEND_URL="http://app:12005"; docker compose -f compose.prod.yml up -d --no-deps monitor-fe
cd ..

docker compose -f auto-test-hcc/compose.yml up -d --build
```

`healthz` phải trả `{"ok":true,...}`. Với backend, lệnh `docker compose` nào cũng phải có `-f compose.prod.yml`. Thiếu cờ này thì container nhảy sang mạng khác và web trace trả 502.

## 5. Tạo tài khoản

Mongo trên máy mới trống, chưa có tài khoản hay req nào. Không chép Mongo hoặc thư mục `data/` từ máy khác, vì trong đó có giấy tờ thật.

Thay các phần trong `<>` rồi chạy:

```powershell
cd auto-fill-hcc-backend

# Tài khoản vào web 12008. Script hỏi mật khẩu, tối thiểu 12 ký tự
docker compose -f compose.prod.yml exec app python -m scripts.manage_super_admin --username <ten-admin> --apply

# Tài khoản test của đơn vị đang thử. Mật khẩu tối thiểu 8 ký tự
docker compose -f compose.prod.yml exec app python -m scripts.seed_user --username <ten-test> --password "<mat-khau>" --name "<ten hien thi>" --tinh "Tỉnh Tuyên Quang" --xa "Xã Thượng Lâm"

cd ..
```

Tỉnh và xã quyết định thủ tục nhìn thấy và cơ quan được chọn trên cổng, nên phải ghi đủ tiền tố `Tỉnh`, `Thành phố`, `Xã`, `Phường`.

## 6. Tạo req đầu tiên

1. Mở `chrome://extensions`, bật **Developer mode**, bấm **Load unpacked**, chọn thư mục `auto-fill-hcc-extension`. Extension đã trỏ `http://localhost:12005`, không sửa `api/config.js`.
2. Đăng nhập panel extension bằng tài khoản test.
3. Vào thủ tục Cấp bản sao trích lục hộ tịch, tải giấy tờ lên và bấm điền.
4. Chép mã req ở ô **Mã hỗ trợ** của panel, hoặc tra ở web Monitor http://localhost:12007.

Chỉ dùng giấy tờ mẫu hoặc giấy tờ của chính người chạy, không dùng hồ sơ người dân. Mỗi ca agent gửi OCR và ảnh giấy tờ lên Anthropic.

## 7. Bật dịch vụ agent

Mở một terminal riêng ở gốc repo và để nguyên:

```powershell
python auto-test-hcc/agents/server.py
```

Kiểm tra ở terminal khác:

```powershell
curl.exe -s http://127.0.0.1:12009/agent-api/health
```

Kết quả phải có `"ok":true` và `"claude":true`.

## 8. Chạy ca đầu tiên

Mở http://localhost:12008, đăng nhập tài khoản super_admin, rồi làm theo [mục 3 của KE-HOACH.md](KE-HOACH.md#3-cách-chạy-một-ca).

Bản sửa đạt nằm trong thư mục làm việc, chưa commit. Người chạy đọc patch trên web rồi tự quyết định commit, hoặc bấm **Hoàn tác bản sửa** để bỏ.

## 9. Quy tắc khi dùng

- Không commit `.env`, `auto-test-hcc/runs/` và `auto-test-hcc/.profile/`. `runs/` chứa giấy tờ, `.profile/` chứa phiên VNeID.
- Bot không được nộp hồ sơ. Không gỡ lớp chặn nộp trong `agents/browser.py`, không thêm cờ tắt.
- Một ca thường tốn 2 đến 6 USD theo giá niêm yết, trần 30 USD.

## 10. Lỗi hay gặp

| Hiện tượng | Xử lý |
| --- | --- |
| OCR hoặc LLM báo timeout, không kết nối được | Bật Tailscale và kiểm tra máy đã vào đúng mạng |
| `/agent-api/health` có `"claude":false` | Cài Claude Code, đăng nhập, rồi bật lại dịch vụ agent |
| Web Monitor báo `INVALID_CREDENTIALS` | `monitor-fe` đang trỏ server. Chạy lại lệnh `$env:BACKEND_URL` ở bước 4 |
| Tài khoản tạo ở bước 5 không đăng nhập được web quản lý 12006 | Đúng như thiết kế: 12006 trỏ server theo `.env`, không đọc Mongo trên máy |
| Web từ chối tạo ca, báo extension sai địa chỉ | `auto-fill-hcc-extension/api/config.js` phải trỏ `http://localhost:12005` |
| Extension báo mất kết nối dù `healthz` vẫn tốt | `wslrelay` giữ cổng 12005. Dừng tiến trình này, khởi động lại Docker là chưa đủ |
| Docker build treo hoặc báo lỗi 500 | Tắt Docker Desktop, chạy `wsl --shutdown`, mở lại |
| Bot kẹt, web hiện khung vàng | Làm đúng việc khung vàng ghi trên cửa sổ bot, rồi bấm nút trong khung |
