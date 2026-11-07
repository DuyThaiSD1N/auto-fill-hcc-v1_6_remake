# auto-test-hcc

Web Agent tự sửa (cổng 12008) và dịch vụ agent (cổng 12009). Tách riêng khỏi `auto-fill-hcc-backend`, nên bản BE dán đè không xoá
mất phần này.

Đội tester đọc [KE-HOACH.md](KE-HOACH.md): cách bật hệ thống, cách chạy một ca, kịch bản kiểm thử. Team F19 cài máy mới theo [HUONG-DAN-F19.md](HUONG-DAN-F19.md). File này dành cho người sửa code.

| Thư mục | Nội dung |
| --- | --- |
| `web/` | Trang web, chạy trong Docker. `src/lab/auto/` là tab chính, `src/lab/Results.tsx` là tab Kết quả điền. |
| `agents/` | Dịch vụ điều phối, chạy trên máy host vì cần `claude`, repo, `docker` và cửa sổ trình duyệt. |
| `runs/` | Dữ liệu từng job. Có giấy tờ, đã gitignore, không commit. |
| `.profile/` | Profile Chromium của bot, giữ phiên VNeID. Đã gitignore, agent bị chặn đọc. |

## File trong `agents/`

| File | Việc |
| --- | --- |
| `server.py` | API, xác thực super_admin, hàng đợi một luồng |
| `orchestrator.py` | Máy trạng thái của một job |
| `browser.py` | Điều khiển Chromium và panel extension, lớp chặn nộp |
| `claude_runner.py` | Chạy agent bằng `claude -p`, giới hạn tool và phạm vi sửa |
| `roles.py` | Prompt và schema từng vai |
| `scoring.py` | Chấm tiêu chí, dò hồi quy |
| `codeguard.py` | Ảnh chụp, hoàn tác, phạm vi sửa, quét dữ liệu thật trong patch |
| `verify.py` | Test BE, test extension, build Docker, healthz |
| `evidence.py` | Gom chứng cứ của req từ Mongo local |
| `replay.py` | Đăng nhập backend, xoá cache OCR, chế độ Chỉ gọi backend |

## Quy tắc khi sửa

- Không nới lớp chặn nộp trong `browser.py`, không thêm cờ tắt.
- Mọi việc quyết định kết quả do mã chạy, không để agent tự báo. Agent không có Bash.
- Vào thủ tục phải đi qua cơ chế của extension (`#destGoBtn`, `agency-select.js`), không viết thao tác bấm nút cổng riêng.
- Bot không nối Playwright khi đang ở màn SSO, và phải rời ra trong lúc chờ agent: Playwright đồng bộ chỉ xử lý mạng khi đang có
  lệnh gọi, nối mà ngồi chờ thì request của trang bị treo.
- `togglePanel` là công tắc: panel thu nhỏ thành `#autofill-hcc-bubble` thì phải bấm bong bóng, toggle là đóng mất.
- Không tự ký token bằng secret của backend. Chạy lại dùng `/auth/login` với mật khẩu người dùng nhập, chỉ giữ trong RAM.

## Test

```powershell
cd auto-test-hcc/agents
python -m pytest tests -q -p no:cacheprovider
```

`tests/test_browser.py` kiểm lớp chặn nộp bằng cú click thật trong Chromium headless.

## Đồng bộ mô phỏng form

`web/src/simulations/` và các component trong `web/src/components/` là bản chép từ `auto-fill-hcc-backend/monitor-fe/src/`. Thêm mẫu mô
phỏng cho thủ tục mới ở Monitor rồi muốn tab Kết quả điền thấy thì chép lại thư mục `simulations/`.

## Đổi model

Biến môi trường khi bật dịch vụ: `AUTOTEST_MODEL_ANALYST` (mặc định `sonnet`), `AUTOTEST_MODEL_ARBITER` và `AUTOTEST_MODEL_FIXER`
(mặc định `opus`). `AUTOTEST_JOB_BUDGET_USD` đổi trần chi phí mỗi ca.
