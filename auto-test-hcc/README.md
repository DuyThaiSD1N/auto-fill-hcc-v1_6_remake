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
| `devjob.py` | Job "Thêm thủ tục mới": nhận tệp kéo thả, chuyển Excel/Word sang chữ, thêm link `ke_khai_links.json`, cho agent làm pipeline, kiểm chứng, chạy thử file mẫu |

## Duyệt bản sửa (job sửa lỗi)

- Bản sửa qua test thì `Orchestrator._await_approval` dừng ở giai đoạn `approve` và ghi `job.approval` (vòng, file, `canRetry`,
  `timeoutMin`). Chưa build Docker, chưa đánh dấu nạp lại extension. Web hiện khung duyệt và gọi
  `POST /agent-api/jobs/{id}/approval` với `{round, decision: approve | retry | reject, note}`.
- `approve`: build, nạp extension, chạy kiểm. `retry`: hoàn tác, góp ý vào `attempts[].gop_y_nguoi_duyet`, hội đồng đọc ở vòng sau
  (bắt buộc có góp ý, vòng cuối không cho). `reject` hoặc quá `AUTOTEST_APPROVAL_TIMEOUT_MIN` (60) phút: hoàn tác, kết luận `not_approved`.
- API từ chối khi `round` không khớp vòng đang chờ, để trang cũ không duyệt nhầm patch của vòng sau. Ai duyệt ghi ở `rounds[].approval.by`.
- Người duyệt sửa tay file trong lúc chờ thì mã build theo nội dung trên đĩa, giữ patch lúc duyệt ở `fix.approvedPatch` và cảnh báo.
- Không thêm cờ bỏ qua bước duyệt. Job "Thêm thủ tục mới" chưa có bước này.

## Hết vòng mà chưa đạt (Cần người xem)

- Mỗi vòng trượt vẫn hoàn tác để vòng sau làm lại từ code gốc, nhưng `_round_failed` giữ lại thay đổi của vòng đó trong
  `self.kept`. Hết vòng thì `_keep_last_fix` build trả Docker về code gốc trước, rồi đặt lại code của vòng trượt gần nhất và
  ghi `job.fix` với `unverified: true` để nút Hoàn tác bản sửa dùng được. Không build bản này.
- Không đặt lại khi: người duyệt đã bác vòng đó (`keep=False`), patch lộ dữ liệu thật của hồ sơ, hoặc file đã bị sửa sau khi hoàn tác.

## Job "Thêm thủ tục mới"

- Web gửi một request multipart `/agent-api/dev/jobs`: ô `meta` là JSON thông tin thủ tục, tệp theo 3 nhóm `mapping`, `attach`, `samples`.
  nginx của test-fe cho `/agent-api/` nhận tới 250 MB.
- Link kê khai do mã thêm (`json.dumps(indent=2)` ra đúng định dạng file), không để agent tự viết. Link nằm trong danh sách file job đã chạm,
  nên dừng hay bấm hoàn tác đều gỡ luôn.
- Agent đã viết code rồi mới lỗi (hết `DEV_MAX_REPAIRS` lần, sửa ngoài phạm vi, agent chết, chạy thử lỗi) thì để yên code đó cho người
  xem (`_keep_dev_code`, người dùng yêu cầu 2026-11-09): ghi `job.fix` với `unverified: true` để nút Hoàn tác thủ tục dùng được, không
  build bản này (stack đã nhận thì build lại về code cũ rồi đặt code agent trở lại). Chỉ bấm Dừng mới hoàn tác ngay. Patch lộ dữ liệu
  thật của file mẫu thì vẫn hoàn tác.
- Agent con chạy với `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`: cwd là repo nên nó dùng chung thư mục memory `~/.claude/projects/<repo>/memory`
  với phiên Claude Code của người dùng; tự ghi ghi nhớ vào đó là "sửa ngoài phạm vi" và job dừng (job 1.115590 ngày 2026-11-09).
- Agent được `Write` (tạo thư mục pipeline mới), sửa extension Auto Fill, và extension trợ lý khi bật đưa lên trợ lý. Hoàn tác file tạo
  mới thì dọn luôn thư mục chỉ còn rỗng hoặc `__pycache__`.
- Đạt khi: có thư mục `app/pipelines/<key đổi - thành _>/` và `tests/unit/test_<thư mục>.py`, test pipeline xanh, không có test mới đỏ ở
  backend, extension, `tests/handfree` (khi bật trợ lý), build + healthz được, chạy thử file mẫu ra ít nhất một ô có giá trị, patch không
  chứa dữ liệu thật của file mẫu. Chưa đạt thì trả lỗi lại cho agent (`DEV_MAX_REPAIRS` lần).
- Biến môi trường: `AUTOTEST_DEV_TIMEOUT_MIN` (60), `AUTOTEST_DEV_AGENT_BUDGET_USD` (25), `AUTOTEST_DEV_JOB_BUDGET_USD` (60).

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
