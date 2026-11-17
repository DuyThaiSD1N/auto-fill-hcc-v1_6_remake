# auto-test-hcc

Web Agent tự sửa (cổng 12008) và dịch vụ agent (cổng 12009). Tách riêng khỏi `auto-fill-hcc-backend`, nên bản BE dán đè không xoá
mất phần này.

Đội tester đọc [KE-HOACH.md](KE-HOACH.md): cách bật hệ thống, cách chạy một ca, kịch bản kiểm thử. Team F19 cài máy mới theo [HUONG-DAN-F19.md](HUONG-DAN-F19.md). Cài lên server trolyhoso theo [HUONG-DAN-SERVER.md](HUONG-DAN-SERVER.md). File này dành cho người sửa code.

## Khu làm việc, ca hồi quy, nhánh PR (mặc định trên máy local, từ 17/11/2026)

1. **Khu làm việc** (`agents/workspace.py`, thư mục `~/.autotest-hcc/workspace/`, đổi bằng `AUTOTEST_WORKSPACE_DIR`): phải nằm NGOÀI mọi repo git, nằm trong repo thì Claude lấy repo đó làm gốc và agent đọc nhầm code / chứng cứ (lỗi 17/11, `workspace.prepare` nay chặn). Mỗi ca, agent sửa trong một cây code sạch, KHÔNG phải thư mục
   làm việc của người phát triển. Ba repo thật được clone riêng (`dev-f19/auto-fill-hcc-backend`, `…/auto-fill-hcc-extension`,
   `…/tro-ly-nguoi-dan-extension`) và đặt về tag release mới nhất, tức bản đang chạy production: `v20*`, `autofill-v*`, `handfree-v*`.
   Ép ref khác bằng `AUTOTEST_BE_REF` / `_EXT_REF` / `_TROLY_REF`.
   - Đầu ca: lưu phần ca trước để lại vào `runs/<ca trước>/workspace-left.patch`, dọn sạch, đặt lại tag, xoá chứng cứ của ca khác khỏi khu
     làm việc. Extension trong khu làm việc trỏ backend thử; hai file đó codeguard cấm sửa nên không bao giờ vào commit.
   - Backend thử: `deploy/compose.local.yml`, `127.0.0.1:12025`, project `auto-test-hcc-be`, image `autofill-hcc-be:autotest`, service
     `autotest-app`. Không đặt tên `app`, vì trùng alias với stack 12005. Dùng chung Mongo local nên tài khoản test như cũ. 12005 của người
     phát triển và 12015 (stack toàn trình) không bị đụng. Cây khu làm việc đổi thì `verify.ensure_stack` build lại trước khi chạy lại req.
   - Baseline test khoá theo commit git, nên mọi ca cùng tag dùng chung một baseline.
   - Cửa sổ bot nạp extension của khu làm việc. Cửa sổ cũ nạp extension ở chỗ khác thì bot tự đóng và mở lại; profile giữ nguyên.
2. **Ca hồi quy** (`agents/regression_case.py`, `regression/`): ca đạt có đụng backend → ca ẩn danh trong `regression/cases`, chỉ khi phát lại
   đạt trên bản sửa. Mỗi bản sửa sau phải giữ đạt các ca đang đạt (`verify.compare_regression`). Chạy được trong CI, xem
   [regression/README.md](regression/README.md).
3. **Nhánh PR** (`publish.push_components`): bản sửa đạt → nhánh `agent/<mã ca>` trên đúng repo thật của phần bị sửa, dựng trên tag release,
   kèm link "Mở PR" trên web. Không tạo PR bằng token, không bao giờ push lên main. Tắt bằng `AUTOTEST_WORKSPACE_PUSH=0`.
4. **Agent chỉ thấy khu làm việc** (`claude_runner`): repo của người phát triển bị chặn cả Read lẫn Edit. Prompt đưa đường dẫn chứng cứ
   tuyệt đối trong khu làm việc. OCR + ảnh chụp từng lần chạy lại được chép sang `<chứng cứ>/../replay/<lượt>/` (`_share_replay`).
5. **Bot tự bấm trên cổng** (`browser.auto_advance`, `ADVANCE_JS`): nút xác nhận / chuyển bước ("Xác nhận", "Đồng ý", "Tiếp tục"…),
   ưu tiên trong hộp thoại, chỉ bấm khi nút đứng yên ≥ 4 giây (để agency-select.js của extension tự chọn cơ quan trước). Bước Thông tin
   chủ hồ sơ tự bấm Tiếp tục. Không bao giờ bấm nút có chữ nộp / gửi / lưu / huỷ / xoá / quay lại / ký số. Trang trắng hoặc form không
   lên quá 8 giây thì tự tải lại, tối đa 3 lần, quá nữa mới nhờ người.
6. **Sửa cho Auto Fill hay Trợ lý hồ sơ** (`settings.target`): Trợ lý hồ sơ (mặc định khi req là lượt trợ lý) báo hội đồng đây là kênh
   handfree; bản sửa đụng phần trợ lý thì chạy thêm `tests/handfree` và so với trước khi sửa. Trợ lý hiện chỉ chạy ở chế độ Chỉ gọi
   backend: bot chưa tự lái được luồng chat / wizard của extension trợ lý trên cổng.

Quay về kiểu cũ (sửa thẳng repo người phát triển, build `compose.prod.yml`, 12005): `AUTOTEST_WORKSPACE=0`. Server (cách B) mặc định kiểu cũ.

## Biến môi trường

Dịch vụ đọc thêm `auto-test-hcc/server.env` (gitignore) nếu có.

| Biến | Server trolyhoso | Việc |
| --- | --- | --- |
| `AUTOTEST_SOURCE_MONGO_URI`, `_SOURCE_DB`, `_SOURCE_UPLOADS` | Mongo production (tài khoản `read`), uploads production | Nguồn req, chỉ đọc. Có biến này là chế độ server |
| `AUTOTEST_SOURCE_SSH`, `_SOURCE_SSH_KEY`, `_SOURCE_TUNNEL` | (máy local đọc trolysoao) `nlp@<ip-trolysoao>`, khoá riêng, `12024:127.0.0.1:12004` | `remote.py`: đường hầm tới Mongo + tải tệp qua `deploy/read-uploads.sh`. Vẫn là chế độ local |
| `AUTOTEST_BACKEND`, `AUTOTEST_TEST_MONGO_URI` | 127.0.0.1:12015, Mongo 12014 | Backend thử: chạy lại, xoá cache OCR, đọc trace |
| `AUTOTEST_COMPOSE_FILE` | `deploy/compose.server.yml` | Build backend thử. `config.server_problems()` chặn khởi động nếu thiếu hoặc là `compose.prod.yml` |
| `AUTOTEST_AUTH_BACKEND` | backend production | Kiểm super_admin của web |
| `AUTOTEST_EXTENSION_BACKEND` | `http://localhost:12015` | `browser.preflight` đối chiếu `api/config.js` |
| `AUTOTEST_GIT_REMOTE` | `origin` | `publish.py` commit bản sửa đạt lên nhánh `agent/<mã ca>` bằng index tạm, không đụng thư mục làm việc |
| `AUTOTEST_VNC`, `DISPLAY` | `1`, `:99` | Nút Mở màn hình bot, vé `/agent-api/vnc-ticket` cho nginx `auth_request` |
| `AUTOTEST_DENY_READ_DIRS` | `/opt/autofill-hcc` | Agent không được Read, dù ngoài repo |

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
| `publish.py` | Commit bản sửa đạt lên nhánh `agent/<mã ca>` (mỗi repo thật một nhánh), push, link mở PR |
| `workspace.py` | Khu làm việc: clone riêng, đặt tag release, dọn sạch, trỏ extension sang backend thử |
| `regression_case.py` | Dựng ca hồi quy ẩn danh từ một lượt chạy lại đạt |
| `remote.py` | Đọc req từ server qua SSH (đường hầm Mongo + `deploy/read-uploads.sh`) |

| Thư mục ngoài `agents/` | Việc |
| --- | --- |
| `regression/` | `run.py` + `harness.py` phát lại ca hồi quy trên một cây backend bất kỳ; `cases/` bộ ca; `ci/regression.yml` mẫu CI |
| `deploy/` | `compose.local.yml` (backend thử local), `compose.server.yml` + `setup.sh` (cách B), `read-uploads.sh` (cách A) |

Job "Thêm thủ tục mới" (`devjob.py`, tab cùng tên trên web) đã gỡ ngày 2026-11-09. Job cũ loại này trong `runs/` vẫn nằm trên đĩa
nhưng dịch vụ không nạp lên web.

## Duyệt bản sửa

- Bản sửa qua test thì `Orchestrator._await_approval` dừng ở giai đoạn `approve` và ghi `job.approval` (vòng, file, `canRetry`,
  `timeoutMin`). Chưa build Docker, chưa đánh dấu nạp lại extension. Web hiện khung duyệt và gọi
  `POST /agent-api/jobs/{id}/approval` với `{round, decision: approve | retry | reject, note}`.
- `approve`: build, nạp extension, chạy kiểm. `retry`: hoàn tác, góp ý vào `attempts[].gop_y_nguoi_duyet`, hội đồng đọc ở vòng sau
  (bắt buộc có góp ý, vòng cuối không cho). `reject` hoặc quá `AUTOTEST_APPROVAL_TIMEOUT_MIN` (60) phút: hoàn tác, kết luận `not_approved`.
- API từ chối khi `round` không khớp vòng đang chờ, để trang cũ không duyệt nhầm patch của vòng sau. Ai duyệt ghi ở `rounds[].approval.by`.
- Người duyệt sửa tay file trong lúc chờ thì mã build theo nội dung trên đĩa, giữ patch lúc duyệt ở `fix.approvedPatch` và cảnh báo.
- Không thêm cờ bỏ qua bước duyệt.

## Hết vòng mà chưa đạt (Cần người xem)

- Mỗi vòng trượt vẫn hoàn tác để vòng sau làm lại từ code gốc, nhưng `_round_failed` giữ lại thay đổi của vòng đó trong
  `self.kept`. Hết vòng thì `_keep_last_fix` build trả Docker về code gốc trước, rồi đặt lại code của vòng trượt gần nhất và
  ghi `job.fix` với `unverified: true` để nút Hoàn tác bản sửa dùng được. Không build bản này.
- Không đặt lại khi: người duyệt đã bác vòng đó (`keep=False`), patch lộ dữ liệu thật của hồ sơ, hoặc file đã bị sửa sau khi hoàn tác.

## Quy tắc khi sửa

- Không nới lớp chặn nộp trong `browser.py`, không thêm cờ tắt.
- Mọi việc quyết định kết quả do mã chạy, không để agent tự báo. Agent không có Bash.
- Vào thủ tục phải đi qua cơ chế của extension (`#destGoBtn`, `agency-select.js`), không viết thao tác bấm nút cổng riêng.
- Bot không nối Playwright khi đang ở màn SSO, và phải rời ra trong lúc chờ agent: Playwright đồng bộ chỉ xử lý mạng khi đang có
  lệnh gọi, nối mà ngồi chờ thì request của trang bị treo.
- `togglePanel` là công tắc: panel thu nhỏ thành `#autofill-hcc-bubble` thì phải bấm bong bóng, toggle là đóng mất.
- Không tự ký token bằng secret của backend. Chạy lại dùng `/auth/login` thật: dịch vụ dựng tài khoản test trên Mongo của backend thử bằng `scripts.seed_user` (cùng username, xã, tỉnh với tài khoản đã điền req, cờ `autotest_shadow`, mật khẩu ngẫu nhiên chỉ giữ trong RAM). Chỉ ghi đè tài khoản có cờ đó; trùng tài khoản test của người khác thì dùng `autotest-<username>`.
- Agent con chạy với `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`: cwd là repo nên nó dùng chung thư mục memory `~/.claude/projects/<repo>/memory`
  với phiên Claude Code của người dùng; tự ghi ghi nhớ vào đó là "sửa ngoài phạm vi" và job dừng (job 1.115590 ngày 2026-11-09).

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
