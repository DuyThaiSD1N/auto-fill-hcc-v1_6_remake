# auto-test-hcc

Web Agent tự sửa (cổng 12008) và dịch vụ agent (cổng 12009). Tách riêng khỏi `auto-fill-hcc-backend`, nên bản BE dán đè không xoá
mất phần này.

**Từ 18/11/2026 không còn chạy trên cổng thật.** Bỏ hẳn Chromium (bot trên cổng, trình chạy bot, màn hình ảo / noVNC). Mọi lần chạy lại
gọi backend thử với giấy tờ của req (OCR mới mỗi lần) và chấm trên các trường backend trả. Tab "Kết quả điền" hiện trường nào nhận giá
trị gì, mô phỏng trên form đã khai của thủ tục (`web/src/simulations`) như web trace, có thêm "Lượt gốc (req)" để so. Agent chỉ sửa
backend: lỗi ở extension (backend trả đúng mà form không nhận) thì báo cáo, vì không chạy extension nên không kiểm chứng được.

Đội tester đọc [KE-HOACH.md](KE-HOACH.md): cách bật hệ thống, cách chạy một ca, kịch bản kiểm thử. Team F19 cài máy mới theo [HUONG-DAN-F19.md](HUONG-DAN-F19.md). Cài lên server production theo [HUONG-DAN-SERVER.md](HUONG-DAN-SERVER.md) mục B. File này dành cho người sửa code.

## Trong Monitor (từ 23/11/2026)

Nhóm menu **Auto test** của Monitor 12007 gồm Agent tự sửa (`monitor-fe/src/autotest/agent/`, chép từ `web/src/lab/auto/` + `Results`
+ `engine`; đổi lớp `lab-dot`/`lab-step` thành `fix-dot`/`fix-step` vì trùng `autotest.css`) và 5 màn lab (`agents/lab.py`, API
`/agent-api/lab/*`). Monitor gọi dịch vụ qua nginx (`AGENT_URL`), dùng chung phiên super_admin của Monitor. Web 12008 vẫn giữ: dùng
riêng được, và trên server là cầu nối Monitor → `127.0.0.1:12009`. Sửa giao diện Agent tự sửa ở một bên thì chép sang bên kia.

Hai bố cục: monorepo (thư mục này cạnh `auto-fill-hcc-backend/`) và repo backend `dev-f19/auto-fill-hcc-backend` nhánh `auto-fix`
(thư mục này nằm trong gốc repo backend, cách cài lên server). `config.BE_REPO_LAYOUT` tự nhận ra; bố cục repo backend luôn dùng khu
làm việc vì không có code extension.

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
2. **Ca hồi quy** (`agents/regression_case.py`, `regression/`): ca đạt có đụng backend → ca ẩn danh trong `regression/cases`, chỉ khi phát lại
   đạt trên bản sửa. Mỗi bản sửa sau phải giữ đạt các ca đang đạt (`verify.compare_regression`). Chạy được trong CI, xem
   [regression/README.md](regression/README.md).
3. **Nhánh PR** (`publish.push_components`): bản sửa đạt → nhánh `agent/<mã ca>` trên đúng repo thật của phần bị sửa, dựng trên tag release,
   kèm link "Mở PR" trên web. Không tạo PR bằng token, không bao giờ push lên main. Tắt bằng `AUTOTEST_WORKSPACE_PUSH=0`.
4. **Agent chỉ thấy khu làm việc** (`claude_runner`): repo của người phát triển bị chặn cả Read lẫn Edit. Prompt đưa đường dẫn chứng cứ
   tuyệt đối trong khu làm việc. OCR + kế hoạch từng lần chạy lại được chép sang `<chứng cứ>/../replay/<lượt>/` (`_share_replay`).
5. **Sửa cho Auto Fill hay Trợ lý hồ sơ** (`settings.target`): Trợ lý hồ sơ (mặc định khi req là lượt trợ lý) báo hội đồng đây là kênh
   handfree; bản sửa đụng phần trợ lý thì chạy thêm `tests/handfree` và so với trước khi sửa.

Quay về kiểu cũ (sửa thẳng repo người phát triển, build `compose.prod.yml`, 12005): `AUTOTEST_WORKSPACE=0`. Server (cách B) mặc định kiểu cũ.

## Biến môi trường

Dịch vụ đọc thêm `auto-test-hcc/server.env` (gitignore) nếu có.

| Biến | Server trolyhoso | Việc |
| --- | --- | --- |
| `AUTOTEST_SOURCE_MONGO_URI`, `_SOURCE_DB`, `_SOURCE_UPLOADS` | Mongo production (tài khoản `read`), uploads production | Nguồn req, chỉ đọc. Có biến này là chế độ server |
| `AUTOTEST_SOURCE_SSH`, `_SOURCE_SSH_KEY`, `_SOURCE_TUNNEL` | (máy local đọc trolysoao) `nlp@<ip-trolysoao>`, khoá riêng, `12024:127.0.0.1:12004` | `remote.py`: đường hầm tới Mongo + tải tệp qua `deploy/read-uploads.sh`. Vẫn là chế độ local |
| `AUTOTEST_ARCHIVE_URL`, `_USER`, `_PASSWORD` | kho "Quản lý nội bộ" (tài khoản viewer, chỉ trong server.env) | `archive.py`: req mà production đã xoá sau ~30 phút thì lấy từ kho (`/api/runs/<mã req>`, tệp theo sha256) |
| `AUTOTEST_PUBLISH_WEB` | `12018:127.0.0.1:12008` | Đường hầm ngược đưa web lên server; dịch vụ ghi PID ở `runs/_tunnel_pids.txt`, khởi động thì dọn đường hầm mồ côi |
| `AUTOTEST_BACKEND`, `AUTOTEST_TEST_MONGO_URI` | 127.0.0.1:12015, Mongo 12014 | Backend thử: chạy lại, xoá cache OCR, đọc trace |
| `AUTOTEST_COMPOSE_FILE` | `deploy/compose.server.yml` | Build backend thử. `config.server_problems()` chặn khởi động nếu thiếu hoặc là `compose.prod.yml` |
| `AUTOTEST_AUTH_BACKEND` | backend production | Kiểm super_admin của web |
| `AUTOTEST_EXTENSION_BACKEND` | `http://localhost:12015` | `workspace.point_extension` trỏ extension khu làm việc về backend thử |
| `AUTOTEST_GIT_REMOTE` | `origin` | `publish.py` commit bản sửa đạt lên nhánh `agent/<mã ca>` bằng index tạm, không đụng thư mục làm việc |
| `AUTOTEST_DENY_READ_DIRS` | `/opt/autofill-hcc` | Agent không được Read, dù ngoài repo |

| Thư mục | Nội dung |
| --- | --- |
| `web/` | Trang web, chạy trong Docker. `src/lab/auto/` là tab chính, `src/lab/Results.tsx` là tab Kết quả điền. |
| `agents/` | Dịch vụ điều phối, chạy trên máy host vì cần `claude`, repo và `docker`. |
| `runs/` | Dữ liệu từng job. Có giấy tờ, đã gitignore, không commit. |

## File trong `agents/`

| File | Việc |
| --- | --- |
| `server.py` | API, xác thực super_admin, hàng đợi một luồng |
| `orchestrator.py` | Máy trạng thái của một job |
| `claude_runner.py` | Chạy agent bằng `claude -p`, giới hạn tool và phạm vi sửa |
| `roles.py` | Prompt và schema từng vai |
| `scoring.py` | Chấm tiêu chí, dò hồi quy |
| `codeguard.py` | Ảnh chụp, hoàn tác, phạm vi sửa, quét dữ liệu thật trong patch |
| `verify.py` | Test BE, test extension, build Docker, healthz |
| `evidence.py` | Gom chứng cứ của req từ Mongo local |
| `replay.py` | Đăng nhập backend, xoá cache OCR, chạy lại req qua `/api/v2/process` (điền hoặc đính kèm) |
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

## Test lượt đính kèm (từ 17/11/2026)

Web nhận cả mã req của lượt đính kèm (mã hỗ trợ extension hiện sau khi đính), tự nhận loại lượt, không có ô chọn.
Đưa mã lượt điền thì ô tra req gợi ý các lượt đính kèm cùng hồ sơ (`traces.kind=attach` cùng `dossier_id`).

- `evidence.lookup` / `collect` nhận `kind=attach` từ Mongo nguồn và kho lưu trữ (`runs.attach`). Lượt extension tự đính
  (`clientAttachmentCase`) bị từ chối: không có kế hoạch backend để chạy lại. Chứng cứ thêm `attach_plan.json` (kế hoạch, tệp #n
  kèm số trang đếm bằng PyMuPDF / pypdf, `splitDocuments`, `portalRows` = dòng extension đọc trên cổng lúc đó).
- Kế hoạch quy thành **ô ảo** (`scoring.attach_fields`) đặt vào `fields`, nên bảng ô × lần, tiêu chí của trọng tài, hồi quy và
  độ giống lượt gốc dùng nguyên máy chấm của lượt điền. Khoá: `dòng: <tên dòng>` (giấy + trang `[#tệp:trang]`), `loại: <detectedType>`,
  `tệp #n` (trang nào vào dòng nào), `tổng: số mục | trang thiếu | trang trùng | lỗi`. Dòng extension tự thêm mang tên giấy LLM đặt
  gom chung khoá `dòng: Thêm mới` để khoá không đổi giữa các lần chạy.
- Chạy lại: `replay.run_once` gửi `/api/v2/process` với `action=attach`, bỏ `sessionId` / `dossierId`, giữ `attachmentContext`,
  `splitDocuments`; bỏ `replaceFiles` (tệp nén cỡ MB) khỏi kết quả, kế hoạch từng lần ở `replay/<lượt>/run<n>_plan.json`.
- Ca đính kèm không sinh ca hồi quy: bộ phát lại thay tệp bằng ảnh giả 1 trang, planner lại chia giấy theo trang của tệp thật.
- Tab "Kết quả đính kèm" dựng bảng thành phần hồ sơ từ kế hoạch từng lần (`AttachSimulation`), có cả lượt gốc.
- Chưa làm: lượt đính kèm của Trợ lý hồ sơ.

## Thủ tục có thanh tra (điền đợt 2, từ 26/11/2026)

Thủ tục khai `"secondPass"` trong `app/procedures/registry.py` có lớp thanh tra (`app/pipelines/<pipeline>/thanh_tra/`, khung
`_shared/thanh_tra`, `app/second_pass`): sau lượt điền đầu, thanh tra đọc lại OCR độc lập, toà án xử chỗ lệch, bản vá ghi lại vài ô.

- `evidence.second_pass_kind` đọc cờ trong registry (khớp `PROCEDURES` thật), `thanh_tra_info` gắn `case.thanhTra` = {has, kind,
  dir, ran, patched, outcomes}. Lượt gốc có `process_requests.second_pass` thì chứng cứ thêm `second_pass.json` (bản vá + biên bản),
  `fields_dot1.json` (lượt điền đầu), còn `fields.json` là giá trị CUỐI (`scoring.merge_patch`).
- Chạy lại: `replay.second_pass_options` chỉ khai `fillSupports` secondPass* khi lượt gốc có chạy thanh tra (lượt gốc không chạy thì
  bỏ, cho giống). `wait_second_pass` đọc collection `second_pass` của backend thử (≤ 90 s), `apply_second_pass` ghép bản vá vào
  `response.fields`, giữ `firstPassFields`, ghi `run<n>_second_pass.json`. Bảng `reproduce.json` có `dot1` / `originalDot1` ở ô bị vá.
  Máy chấm trên giá trị cuối. Lần chạy không có kết quả thanh tra thì web cảnh báo.
- Backend thử bật `SECOND_PASS_ENABLED=true` (mọi tài khoản, hạn 60 s, 10 lượt song song) trong `deploy/compose.local.yml` và
  `compose.server.yml`. Khoá stack gồm cả nội dung file compose (`verify._stack_key`) nên đổi env là tự dựng lại. Kiểu cũ
  (`AUTOTEST_WORKSPACE=0`, chạy lại trên 12005) không bật thanh tra.
- Hội đồng: thêm vai `thanh_tra` ("Soát thanh tra", `roles.THANH_TRA_ANALYST`), cause `thanh_tra`, mục "Lớp thanh tra" + quy tắc cân
  bằng trong `roles._thanh_tra_note`: lượt điền đầu là nguồn chính, thanh tra là lưới an toàn; lượt đầu đúng mà thanh tra đổi sai →
  sửa thanh tra; lượt đầu sai → sửa lượt đầu, không vá thanh tra để chữa lỗi gốc; không sửa cả hai cho một ô; thanh tra phải đọc giấy
  độc lập. Trọng tài ghi `balance`.
- Bản sửa trong `thanh_tra/` không sinh ca hồi quy (lượt soát chạy nền với context rỗng, bộ phát lại chỉ phát lượt đầu).

## Tốc độ họp (27/11/2026)

Đo 11 ca 7–17/11: vòng độc lập 30–70 s, phản biện 40–107 s (~1,5 USD), trọng tài Opus 50–280 s. Người phản biện mở lại cả hồ sơ
(8–21 lượt tool) và mọi người phải viết lại nguyên ý kiến, nên vòng phản biện chậm; khi cả hội đồng cùng một nguyên nhân ≥ 80 % thì
vòng này chưa lần nào đổi kết luận. Đã đổi:

- `Orchestrator._debate_skip_reason`: mọi thành viên cùng một cause (khác `unknown`), độ tin cậy ≥ `_NO_DEBATE_CONFIDENCE` (80) thì
  bỏ phản biện, kể cả khi cause sửa được; `rounds[].debate.consensus = True` và trọng tài nhận `roles._CRITIC_CHECKS` để tự soát.
  Ý kiến khác nhau hoặc có người dưới 80 % thì vẫn phản biện như cũ.
- `REVIEW_SCHEMA` chỉ bắt `cause / confidence / summary / stance / rebuttal`; `evidence` chỉ ghi bằng chứng mới, `proposal` khi đổi.
  Người phản biện chỉ mở đúng file / dòng nghi ngờ.
- Trọng tài nhận sẵn danh sách khoá field hợp lệ (`scoring.known_fields`), khỏi mở `reproduce.json` để tra và bớt trượt vòng vì sai khoá.
- Lập lại kế hoạch theo góp ý: tiếp phiên cũ của trọng tài (`rounds[].decision.sessionId`, `roles.replan_prompt`), chỉ gửi góp ý; tiếp
  phiên lỗi thì lập lại từ đầu như trước.
- Mỗi ý kiến / quyết định ghi `seconds`, log "Xong sau N giây" theo từng thành viên, để đo lại về sau (`_public_opinion` bỏ trường này
  khỏi prompt của agent khác).

## Cách xem cho tester (từ 26/11/2026)

Trang job có nút "Dễ hiểu / Đầy đủ kỹ thuật" (`localStorage` `autotest.agent.view`, mặc định Dễ hiểu). Khung "Tóm tắt dễ hiểu"
(`PlainSummary`): sơ đồ đường đi dữ liệu tô bước gây lỗi (theo cause của trọng tài, chưa có thì số đông hội đồng), kết luận,
thanh tra, kết quả trước / sau sửa, việc tiếp theo, giải thích từ ngữ. Chữ đời thường lấy từ `plain` của trọng tài
(`DECISION_SCHEMA`, bắt buộc) và agent sửa (`FIX_SCHEMA`), kết luận ghi `report.plain`. Chế độ Dễ hiểu thu gọn ý kiến hội đồng,
file, patch, từng bộ test vào mục mở được (`Tech`).

## Duyệt kế hoạch sửa (trước khi agent sửa code)

- Trọng tài chọn `fix_code` và tiêu chí chưa đạt trên code hiện tại thì `Orchestrator._await_plan` dừng ở giai đoạn `plan`, ghi
  `job.planApproval` (`round`, `revision`, `canRevise`, `timeoutMin`). Web hiện khung duyệt kế hoạch và gọi
  `POST /agent-api/jobs/{id}/plan` với `{round, revision, decision: approve | retry | reject, note}`.
- `approve`: agent sửa theo kế hoạch. `retry`: trọng tài lập lại kế hoạch có góp ý (`roles.arbiter_prompt(..., plan_notes, previous)`),
  rồi hỏi lại; tối đa `_PLAN_REVISIONS` (3) lần mỗi vòng, kế hoạch cũ lưu ở `rounds[].planHistory`. `reject` hoặc quá giờ: kết luận
  `not_approved`, chưa đụng dòng code nào. Kết quả từng lần duyệt ở `rounds[].planReviews`.
- API từ chối khi `round` / `revision` không khớp: trang cũ không duyệt nhầm kế hoạch đã lập lại.

## Duyệt bản sửa

- Bản sửa qua test thì `Orchestrator._await_approval` dừng ở giai đoạn `approve` và ghi `job.approval` (vòng, file, `canRetry`,
  `timeoutMin`). Chưa build Docker. Web hiện khung duyệt và gọi
  `POST /agent-api/jobs/{id}/approval` với `{round, decision: approve | retry | reject, note}`.
- `approve`: build backend thử, chạy kiểm. `retry`: hoàn tác, góp ý vào `attempts[].gop_y_nguoi_duyet`, hội đồng đọc ở vòng sau
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

- Mọi việc quyết định kết quả do mã chạy, không để agent tự báo. Agent không có Bash.
- Agent không được sửa extension (`claude_runner` không cấp quyền, `codeguard` coi là ngoài phạm vi): không có lượt chạy nào kiểm được.
- Không tự ký token bằng secret của backend. Chạy lại dùng `/auth/login` thật: dịch vụ dựng tài khoản test trên Mongo của backend thử bằng `scripts.seed_user` (cùng username, xã, tỉnh với tài khoản đã điền req, cờ `autotest_shadow`, mật khẩu ngẫu nhiên chỉ giữ trong RAM). Chỉ ghi đè tài khoản có cờ đó; trùng tài khoản test của người khác thì dùng `autotest-<username>`.
- Agent con chạy với `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`: cwd là repo nên nó dùng chung thư mục memory `~/.claude/projects/<repo>/memory`
  với phiên Claude Code của người dùng; tự ghi ghi nhớ vào đó là "sửa ngoài phạm vi" và job dừng (job 1.115590 ngày 2026-11-09).

## Test

```powershell
cd auto-test-hcc/agents
python -m pytest tests -q -p no:cacheprovider
```

## Đồng bộ mô phỏng form

`web/src/simulations/` và các component trong `web/src/components/` là bản chép từ `auto-fill-hcc-backend/monitor-fe/src/`. Thêm mẫu mô
phỏng cho thủ tục mới ở Monitor rồi muốn tab Kết quả điền thấy thì chép lại thư mục `simulations/`.

## Đổi model

Biến môi trường khi bật dịch vụ: `AUTOTEST_MODEL_ANALYST` (mặc định `sonnet`), `AUTOTEST_MODEL_ARBITER` và `AUTOTEST_MODEL_FIXER`
(mặc định `opus`). `AUTOTEST_JOB_BUDGET_USD` đổi trần chi phí mỗi ca.
