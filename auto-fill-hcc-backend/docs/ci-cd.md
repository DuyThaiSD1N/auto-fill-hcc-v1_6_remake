# CI/CD backend — từ code lên prod

Tài liệu cho thành viên đẩy code backend (`auto-fill-hcc-backend`) lên server prod.
Quy trình nhánh, PR, giải conflict: xem [CONTRIBUTING.md](../CONTRIBUTING.md).

## Tóm tắt

```
PR vào main ──► CI (test + build web) ──► merge vào main
                                              │
                    git tag vYYYY.MM.DD[.n] ──┘  (gắn lên commit đã có trong main)
                                              │
Release:  kiểm tag ─► test ─► build 3 image ─► đẩy GHCR ─► deploy prod ─► kiểm /healthz
                                                                            │
                                                     không đạt ─► server tự quay về bản trước
```

- **Không có lệnh deploy tay.** Push tag là prod tự lên bản mới, mất khoảng 4–6 phút.
- **Không gắn tag = không lên prod.** Merge vào `main` chỉ chạy CI, prod không bị đụng.
- **Quay về bản cũ:** chạy workflow **Deploy (chọn tag)**, khoảng 1 phút, không build lại.

## 1. CI — kiểm mỗi PR và mỗi push lên `main`

File `.github/workflows/ci.yml`, gồm 3 job:

| Job | Kiểm gì |
|---|---|
| **Backend (smoke + pytest)** | Import registry thủ tục (core + handfree) và `app.main`; chạy pytest 4 thư mục `tests/unit`, `tests/handfree/unit`, `tests/integration`, `tests/handfree/integration` (Python 3.11, cùng bản với image prod) |
| **Build fe** | `npm ci` + `npm run build` (tsc + vite) |
| **Build monitor-fe** | như trên |

- Kết quả hiện ngay trên trang PR. **CI đỏ thì không merge.**
- Xem lỗi: bấm job đỏ → mở bước `Pytest` (hoặc `Build`) → kéo xuống phần `FAILED`.
- Chạy y như CI trên máy mình trước khi đẩy:
  ```bash
  .venv/bin/pip install -r requirements-dev.txt
  .venv/bin/python -m pytest tests/unit tests/handfree/unit tests/integration tests/handfree/integration -q
  ```
- Test không cần Mongo, `.env` hay mạng (`tests/conftest.py` chặn hết), nên máy nào cũng chạy được.
- Push mới lên cùng nhánh thì lượt CI cũ bị huỷ, chỉ lượt mới nhất được tính.

## 2. Đẩy lên prod

### Trước khi gắn tag

- [ ] Code đã **merge vào `main`** và CI trên `main` **xanh**.
- [ ] Tính năng cần biến `.env` mới → đã nhờ người quản trị thêm vào `.env` trên server **trước**
      (CD không sửa `.env`).
- [ ] Cần chạy script, vá dữ liệu hay tạo index Mongo → làm riêng, CD không tự chạy.
- [ ] Báo nhóm một câu: "mình lên prod bản X". Hai người gắn tag cùng lúc thì các lượt deploy
      xếp hàng chạy lần lượt, và bản lên **sau cùng** là bản prod chạy.

### Gắn tag

```bash
git switch main && git pull                         # tag phải trỏ vào commit ĐÃ có trong main
git fetch --tags && git tag --sort=-v:refname | head -3   # xem số tag đã dùng hôm nay

git tag v2026.10.14 && git push origin v2026.10.14  # lần đầu trong ngày
# cùng ngày, lần 2, lần 3…: v2026.10.14.1, v2026.10.14.2, …
```

**Mẫu tag:** `vNăm.Tháng.Ngày[.lần]`, ví dụ `v2026.10.14`, `v2026.10.14.1`. Viết năm trước để danh
sách tag tự xếp đúng thứ tự thời gian. Sai mẫu (`v14.10.2026`, `v2026.10.14-fix`,
`release-1`…) thì workflow dừng ngay ở bước kiểm, prod không bị đụng.

### Theo dõi

GitHub → tab **Actions** → **Release** → lượt chạy mang tên tag. Các bước:

| Bước | Thời gian | Ghi chú |
|---|---|---|
| Kiểm tag | vài giây | đúng mẫu + commit nằm trong `main` |
| Test | 1–2 phút | gọi lại đúng CI ở mục 1 |
| Build ×3 | 1–3 phút | `autofill-hcc-be`, `autofill-hcc-fe`, `autofill-hcc-monitor-fe`; có cache nên lần sau nhanh hơn |
| Deploy | khoảng 1 phút | kéo image về server, đổi container, chờ `/healthz` |

### Biết là đã lên

Mở job **Deploy** → bước **SSH → server_deploy.sh**. Hai dòng cuối phải là:

```
healthz: {"ok":true,"version":"v2026.10.14"}
Xong: prod đang chạy v2026.10.14.
```

`/healthz` của BE trả đúng tên tag trong `version`. Server chỉ coi là xong khi `version` khớp đúng
tag vừa gắn, đồng thời trang `fe` và `monitor-fe` trả 200.

## 3. Khi có sự cố

| Thấy gì | Nghĩa là | Làm gì |
|---|---|---|
| Đỏ ở **Kiểm tag**: "sai mẫu" | Tên tag sai | Xoá tag sai (mục dưới), gắn lại đúng mẫu |
| Đỏ ở **Kiểm tag**: "commit chưa có trong main" | Gắn tag trên nhánh phụ hoặc commit chưa merge | Xoá tag, merge vào `main` trước, gắn lại |
| Đỏ ở **Test** | Test hỏng ở commit được gắn tag | Sửa qua PR như thường, merge, gắn **tag mới** (`.n+1`) |
| Đỏ ở **Build** | Dockerfile, thư viện, hoặc `npm run build` lỗi | Như trên |
| Đỏ ở **Deploy**: "Environment production thiếu…" | Thiếu secret/biến cấu hình | Báo người quản trị repo (mục 5) |
| Đỏ ở **Deploy**: "Kéo … lỗi 5 lần" | Server không kéo được image (DNS/mạng); **prod giữ nguyên bản cũ** | Đợi vài phút → **Re-run failed jobs** |
| Đỏ ở **Deploy**: "không lên được — tự quay về bản trước" | Bản mới khởi động lỗi, `/healthz` không đạt trong 120 giây; **prod đã tự về bản trước** | Xem log lỗi app (mục 4), sửa, gắn tag mới |
| Đỏ ở **Deploy**: "Đang có lượt deploy khác chạy" | Có người đang deploy hoặc quay về bản cũ cùng lúc | Đợi lượt kia xong → **Re-run failed jobs** |
| Đỏ ở **Deploy**: lỗi SSH / Tailscale | Hết hạn khoá Tailscale, đổi khoá server… | Báo người quản trị repo |

**Re-run failed jobs** (nút góc phải trang lượt chạy) chỉ chạy lại các job hỏng, không build lại
image đã đẩy xong. Lỗi do code thì **không** chạy lại tag cũ: sửa code, merge, gắn tag mới.

**Xoá tag gắn nhầm** (chỉ khi tag chưa lên prod):

```bash
git push --delete origin v2026.10.14
git tag -d v2026.10.14
```

Không dời tag đã lên prod sang commit khác (`git tag -f`): tên tag phải luôn ứng với đúng một bản đã chạy.

## 4. Quay về bản cũ

Bản mới lên được nhưng có lỗi nghiệp vụ (điền sai, sai luồng…):

1. GitHub → **Actions** → **Deploy (chọn tag)** → **Run workflow**.
2. Ô **Use workflow from** → tab **Tags** → chọn tag của bản chạy tốt trước đó.
3. Bấm **Run workflow**. Khoảng 1 phút, không build lại; image đã có sẵn trên GHCR.

Cũng dùng cách này để deploy lại một tag bất kỳ, ví dụ khi server vừa khởi động lại.
Ô *Use workflow from* phải chọn **tag**: chọn nhánh `main` thì workflow báo lỗi và không làm gì.

Người có SSH vào server có thể quay về ngay bản chạy liền trước, không qua GitHub:

```bash
cd ~/hcc && ./server_deploy.sh rollback
```

Xem log lỗi của app trên server: `docker compose -f compose.prod.yml logs --tail 200 app`.

## 5. Bên trong — dành cho người quản trị

### Workflow

| File | Chạy khi | Việc |
|---|---|---|
| `ci.yml` | PR / push `main` / bấm tay; `release.yml` gọi lại | Test + build web |
| `release.yml` | Push tag `v*` | Kiểm tag → gọi `ci.yml` → build 3 image → đẩy GHCR → gọi `_deploy.yml` |
| `deploy.yml` | Bấm tay, chọn tag | Gọi `_deploy.yml` với tag đã chọn |
| `_deploy.yml` | Chỉ được gọi từ hai file trên | Kiểm đủ 3 image trên GHCR → vào mạng Tailscale → SSH vào server |

- Image: `ghcr.io/dev-f19/<image>:<tag>`, package private. Tag `:buildcache` trong mỗi package là
  cache build, **không** phải bản phát hành; đừng xoá.
- Build truyền `APP_VERSION=<tag>` vào image, nên `/healthz` biết mình là bản nào.

### GitHub Environment `production`

Settings → Environments → `production`. Chỉ ref là tag `v*` mới dùng được environment này.

| Loại | Tên | Là gì |
|---|---|---|
| Secret | `TS_AUTHKEY` | Auth key Tailscale (ephemeral) để runner vào mạng nội bộ của server. **Auth key có hạn dùng (tối đa 90 ngày)**: hết hạn thì bước Tailscale đỏ → tạo key mới, dán đè secret |
| Secret | `DEPLOY_SSH_KEY` | Khoá riêng SSH chỉ dùng để deploy |
| Secret | `DEPLOY_KNOWN_HOSTS` | Dấu vân tay SSH của server (chặn máy giả mạo) |
| Variable | `DEPLOY_USER`, `DEPLOY_HOST` | Tài khoản và địa chỉ Tailscale của server |

### Phía server

- Thư mục deploy: `~/hcc` (có `compose.prod.yml`, `.env`, `data/`).
- Khoá deploy bị **ép** chạy đúng `server_deploy.sh` (`command="…"` trong `authorized_keys`): ai có
  khoá cũng chỉ truyền được tên tag hoặc `rollback`, không chạy được lệnh khác.
- `server_deploy.sh` làm theo thứ tự:
  1. Kéo 3 image của tag (lỗi mạng thì thử lại 5 lần, mỗi lần cách 15 giây).
  2. Gắn nhãn bản đang chạy thành `:prev`, bản mới thành `:latest`.
  3. `docker compose up -d --no-build --no-deps app fe monitor-fe`: **không** đụng Mongo, `.env`, `data/`.
  4. Chờ tối đa 120 giây cho `/healthz` trả đúng `version` và hai trang web trả 200.
  5. Không đạt thì tự quay về `:prev`.
  6. Đạt thì dọn image cũ chạy nền (giữ 3 tag gần nhất của mỗi image).
- Lịch sử deploy: `~/hcc/deploy-history.log`; log dọn image: `~/hcc/prune.log`.
- **Sửa `scripts/server_deploy.sh` trong repo KHÔNG tự cập nhật lên server.** Server chạy bản chép
  tay tại `~/hcc/server_deploy.sh`; sửa xong phải chép lại bằng `scp`.

### Không nằm trong CD

- `.env`, dữ liệu Mongo, index, script vá dữ liệu: làm tay theo nhật ký vận hành.
- Hai extension Chrome: phát hành riêng qua Chrome Web Store, không theo luồng này.
