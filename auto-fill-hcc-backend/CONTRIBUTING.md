# Quy trình đẩy code — tránh conflict và mất code

Repo này nhiều người cùng sửa, và đã nhiều lần **mất tính năng vì merge**: giải conflict bằng cách
chọn nguyên cả file của một bên, hoặc chép file từ máy khác đè vào. Làm theo các bước dưới để
code của người khác không bị nuốt, và code của mình không nuốt người khác.

## 1. Quy trình cho mỗi việc

```bash
# 1. Tạo nhánh từ main mới nhất — mỗi nhánh MỘT việc
git fetch origin
git switch -c fix/khai-tu-noi-cap origin/main

# 2. Sửa, commit nhỏ, message nói rõ làm gì
git commit -m "fix: khai tử không lấy nơi cấp của thẻ người khác"

# 3. Trước khi mở PR: cập nhật từ main, giải conflict NGAY TRÊN NHÁNH MÌNH
git fetch origin
git rebase origin/main            # hoặc: git merge origin/main
.venv/bin/python -m pytest tests/unit tests/handfree/unit tests/integration tests/handfree/integration -q

# 4. Đẩy nhánh rồi mở PR vào main trên GitHub
git push -u origin fix/khai-tu-noi-cap
#    (đã rebase lại nhánh đã đẩy trước đó thì: git push --force-with-lease)
```

5. Chờ CI trên PR xanh (✅ Backend, Build fe, Build monitor-fe).
6. Tự soát tab **Files changed** (mục 3), rồi mới bấm Merge.

**Đặt tên nhánh:** `fix/<việc>`, `feat/<việc>`, `tt/<mã-hoặc-tên-thủ-tục>`. Ví dụ `tt/1.004859-cai-chinh`.

**Nhánh sống ngắn:** merge trong 1–2 ngày. Nhánh để càng lâu thì `main` đi càng xa, conflict càng to.
Không gom nhiều việc không liên quan vào một PR.

## 2. Giải conflict

- **KHÔNG** chọn "Accept Current" / "Accept Incoming" cho **cả file**. Đọc từng khối `<<<<<<< ======= >>>>>>>`;
  thường phải **giữ cả hai bên**. Ví dụ hai người cùng thêm một dòng cấu hình theo tài khoản vào
  cùng chỗ thì cả hai dòng đều phải còn.
- Ở file lớn hay đụng nhau, đọc thêm đoạn ngay trên và dưới chỗ conflict:
  `app/procedures/registry.py`, `app/channels/handfree/chat/flow.py`,
  `app/process/router.py`, `app/channels/handfree/chat/pipeline_runner.py`.
- Giải xong **chạy lại test**, rồi mới commit.
- **KHÔNG chép file từ máy khác / nhánh khác đè vào.** Muốn lấy code của người khác thì dùng
  `git merge` hoặc `git cherry-pick <commit>`.

## 3. Soát diff trước khi merge — bước bắt "nuốt code"

```bash
git diff origin/main...HEAD --stat   # chỉ được thấy những file MÌNH sửa
git diff origin/main...HEAD          # đọc kỹ các dòng bị xoá (-)
```

Trên GitHub là tab **Files changed** của PR. **Dừng lại, đừng merge** nếu thấy:

- dòng bị xoá ở file hoặc đoạn mình không hề động tới;
- số dòng xoá lớn bất thường so với việc mình làm;
- file mình không sửa nhưng vẫn nằm trong danh sách.

## 4. CI

- Mỗi push lên `main` và mỗi PR vào `main` đều chạy CI (`.github/workflows/ci.yml`): smoke import
  registry, pytest 4 thư mục test, build `fe` + `monitor-fe`. Xem kết quả ở trang PR hoặc tab
  **Actions**.
- CI đỏ: bấm vào job đỏ → bước `Pytest` để xem test nào hỏng. **Không merge khi CI đỏ.**
- Test đỏ có thể chính là dấu hiệu code của ai đó vừa bị nuốt. Đừng sửa assert cho xanh khi chưa
  biết vì sao nó đỏ.
- **Thêm test** cho tính năng quan trọng, nhất là cấu hình theo tài khoản / tỉnh (loại hay bị mất
  khi merge). Có test thì lần sau bị nuốt, CI báo ngay.
- Test chạy không cần Mongo, `.env` hay mạng (`tests/conftest.py` chặn). Cài thư viện test bằng:
  `.venv/bin/pip install -r requirements-dev.txt`.

## 5. Không bao giờ

- `git push --force` lên `main`.
- Commit `.env`, mật khẩu, token, khoá API, hay danh sách tài khoản kèm mật khẩu, kể cả trong
  script "chạy một lần". Đã lên GitHub là nằm vĩnh viễn trong lịch sử; xoá file không gỡ được.
  Lỡ commit thì báo ngay để đổi mật khẩu.
- Commit dữ liệu thật của người dân (ảnh giấy tờ, số định danh, họ tên) vào test hay fixture —
  dùng dữ liệu giả.
- Để script quan trọng ở dạng chưa commit. File chỉ nằm trên máy mình mất là mất hẳn.

## 6. Khi một tính năng "tự nhiên biến mất"

```bash
git log --oneline -S "<tên hàm hoặc chuỗi đặc trưng>" -- app/   # commit nào thêm, commit nào xoá
git show <commit> -- <file>                                     # xem đúng đoạn bị xoá
```

Khôi phục **đúng đoạn bị mất**, không revert cả commit (commit đó thường còn thay đổi đúng khác).
Thêm test để lần sau CI bắt được.

## 7. Phát hành lên prod

```bash
git switch main && git pull                          # tag phải trỏ vào commit ĐÃ có trong main
git tag v2026.10.12 && git push origin v2026.10.12     # mẫu vYYYY.MM.DD; cùng ngày lần 2: v2026.10.12.1
```

- Push tag là tự chạy: test → build image → đẩy GHCR → **deploy prod**. Theo dõi ở tab **Actions** → Release.
- Tag sai mẫu, hoặc gắn lên commit chưa merge vào `main` → bị chặn, prod không bị đụng.
- Sau khi lên, `/healthz` phải trả đúng `"version"`; không đạt thì server **tự quay về bản trước**.
- **Quay về bản cũ:** Actions → **Deploy (chọn tag)** → **Run workflow** → ô *Use workflow from* → tab **Tags** →
  chọn tag cũ → Run. Không build lại, khoảng 1 phút.
- Cần biến `.env` mới cho tính năng mới → sửa `.env` trên server **trước** khi gắn tag.
- Xem tag mới nhất: `git tag --sort=-v:refname | head` (năm trước nên tên tag tự xếp đúng thứ tự thời gian).
- Tag cũ dạng `vDD.MM.YYYY` (trước 12/10/2026) vẫn quay về được bằng nút Deploy (chọn tag).

## 8. Phối hợp

- Sắp sửa một file "nóng" ở mục 2 thì báo nhóm một câu, tránh hai người cùng sửa một vùng.
- Không chắc một đoạn code của người khác còn dùng không → hỏi trước khi xoá.
