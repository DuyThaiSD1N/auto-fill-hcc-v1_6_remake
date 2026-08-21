# Khi nào extension tick "Người được ủy quyền" và nhập nhân thân người đó

Áp dụng cho nhóm thủ tục **hộ kinh doanh** trên cổng HkdOnline (`hokinhdoanh.dkkd.gov.vn`), trang
**Người nộp hồ sơ**. Logic nằm trong [`content/procedures/business-registration.js`](../content/procedures/business-registration.js),
hàm `handleCopyPersonPage()`.

> Tài liệu mô tả hành vi **thực tế của code**, không phải quy trình nghiệp vụ mong muốn.

---

## 1. Hai việc TÁCH RỜI nhau

Rất dễ nhầm hai chuyện này là một. Chúng có điều kiện khác nhau và xảy ra độc lập:

| | Việc | Ở bước nào | Điều kiện tóm tắt |
|---|---|---|---|
| **A** | Tick radio `Người được ủy quyền` | bước 1 + bước 2c | tài khoản đăng nhập **khác** chủ hộ |
| **B** | Ghi nhân thân người được ủy quyền vào form | bước 2d + bước 4 | radio **đang** ở ủy quyền **và** hồ sơ có nhân thân khớp tài khoản |

Có A mà không có B (không tìm được nhân thân khớp) là chuyện bình thường — khi đó form giữ nguyên
dữ liệu nút "Sao chép thông tin đăng ký tài khoản".

---

## 2. Các trường hợp TICK radio "Người được ủy quyền"

### 2.1. Lượt 1 — theo phán đoán của backend

Bước 1 điền các field "cấu trúc", trong đó có `ctl00$C$PERS_SUBGroup`. Giá trị do backend quyết ở
`dang_ky_kinh_doanh/process/mapper.py`:

```python
is_self = _submitter_is_owner(values) is not False and not has_multiple_cccd
pers_sub_role = _PERS_SUB_SELF_LABEL if is_self else _PERS_SUB_AUTHORIZED_LABEL
```

Backend tick **"Người được ủy quyền"** khi:

| # | Tình huống trong hồ sơ giấy | Vì sao |
|---|---|---|
| 1 | `NguoiNop_SoDinhDanh` ≠ `ChuHo_SoDinhDanh` | `_submitter_is_owner` trả `False` |
| 2 | Hồ sơ không kê số định danh, `NguoiNop_HoTen` ≠ `ChuHo_HoTen` | so theo họ tên (bỏ dấu) |
| 3 | Hồ sơ có **≥ 2 nhân thân** (`HasMultipleCCCD`, hoặc ≥ 2 candidate) | suy đoán có người nộp thay |

Backend **không biết ai đang đăng nhập cổng**, nên đây chỉ là phán đoán từ giấy tờ. Bước 2c mới là
kết luận cuối.

### 2.2. Lượt 2 — sau khi bấm "Sao chép thông tin đăng ký tài khoản" (bước 2c)

Lúc này form đã có nhân thân **thật** của tài khoản đăng nhập. `matchAccountWithOwner()` so tài khoản
với chủ hộ, gom chủ hộ từ **mọi** nguồn có:

- `pages["chu-ho-kinh-doanh"]` — luồng đăng ký mới, và luồng thay đổi CÓ đổi chủ hộ
- `businessFlow.owner` — chủ hộ hiện tại (luồng thay đổi / chấm dứt, không có trang chủ hộ để đọc)
- `businessFlow.search.value` khi tra cứu bằng **số định danh** chủ hộ

| Kết quả đối chiếu | Hành động | Ghi chú |
|---|---|---|
| Số định danh **hoặc** họ tên khớp bất kỳ nguồn nào | tick lại **"Người có thẩm quyền ký"** | chủ hộ tự nộp; sửa lại nếu lượt 1 tick nhầm |
| **Cả** số **và** tên đều khác **mọi** nguồn | **tick "Người được ủy quyền"** ← *ca chính* | radio AutoPostBack → phải chờ cổng render lại |
| Hồ sơ không có nhân thân chủ hộ nào (`ownerUnknown`) | **không đụng radio** | giữ nguyên cái đang tick, không đoán bừa |

### 2.3. Ngoại lệ Đà Nẵng — KHÔNG BAO GIỜ tick ủy quyền

`forceSelfSubmitter(st)` bật khi tài khoản gắn tỉnh Đà Nẵng (popup đọc `tinh` từ `/auth/me`) **và**
thủ tục nằm trong `FORCE_SELF_SUBMITTER_WORKFLOWS`:

| Thủ tục | `workflow` | Có ép "Người có thẩm quyền ký"? |
|---|---|---|
| Đăng ký thành lập hộ kinh doanh | `create` (mặc định) | **Có** |
| Chấm dứt hoạt động hộ kinh doanh | `dissolution` | **Có** |
| Thay đổi nội dung đăng ký HKD | `change` | Không — chạy quy tắc 2.2 như thường |
| Cấp lại / cấp đổi GCN HKD | `reissue` | Không — chạy quy tắc 2.2 như thường |

Khi ép, hai thứ xảy ra:

1. Bước 1 **loại** `PERS_SUBGroup` khỏi danh sách field cấu trúc → không tick theo backend, đỡ một
   postback thừa rồi lại phải tick ngược.
2. `tickSubmitterSelfRadio()` đảm bảo radio ở "Người có thẩm quyền ký".

**Ép vai trò chỉ ép cái radio.** Người nộp vẫn là người đang đăng nhập, nên khi tài khoản không phải
chủ hộ, code vẫn lấy địa chỉ trên CCCD của chính họ (mục 5), không kéo địa chỉ chủ hộ sang.

---

## 3. Các trường hợp NHẬP nhân thân người được ủy quyền

Chuỗi điều kiện ở bước 2d — **phải đủ cả bốn**:

1. `submitterIsAuthorized()` — radio **thật** trên cổng đang ở "Người được ủy quyền".
   Nhánh Đà Nẵng luôn `false` ở đây nên **không bao giờ** ghi đè nhân thân.
2. `buildSubmitterOverride()` tìm được nhân thân khớp tài khoản (mục 4). Không khớp → `null`, giữ
   nguyên dữ liệu tài khoản.
3. `submitterNeedsRewrite()` — số định danh **hoặc** họ tên trên form đang khác giá trị muốn ghi.
   Đã đúng rồi thì không bật "Sửa đổi dữ liệu" một cách vô ích.
4. `enableSubmitterEdit()` tick được ô **"Sửa đổi dữ liệu"** (tối đa 3 lần). Ô này AutoPostBack; nếu
   cổng reload cả trang thì lượt chạy kế của state machine điền tiếp.

Đủ bốn thì `applySubmitterOverride()` ghi giá trị.

### Ghi lần hai trước khi Lưu

Bước 4 lặp lại đúng chuỗi trên ngay trước khi bấm **Lưu**. Lý do: mỗi postback của cascade địa chỉ
đều làm cổng render lại khối người nộp theo dữ liệu tài khoản, đè mất bản ghi ở bước 2d.

### Field được ghi / không ghi

| Ghi (`SUBMITTER_OVERRIDE_FIELDS`) | Không ghi |
|---|---|
| Họ tên — `FULL_NAMEFld` | Số điện thoại |
| Giới tính — radio `GENDER_IDFld` | Email |
| Ngày sinh — `DATE_OF_BIRTHFld` | Fax / website |
| Số định danh — `PERS_DOC_NOFld` | |

Liên hệ giữ theo tài khoản đang nộp để hồ sơ nhận được thông báo của cổng.

Input đang `disabled`/`readonly` được mở khóa ngay trước khi ghi — input bị disable không được trình
duyệt submit, giá trị sẽ mất sau postback kế tiếp.

---

## 4. Nhân thân lấy từ đâu — thứ tự ưu tiên

`matchSubmitterIdentityCandidate()` chọn trong `__identityCandidates` do backend gửi. Danh sách gồm
**thẻ căn cước trong hồ sơ** và **bên được ủy quyền đọc từ Giấy ủy quyền**.

Thứ tự trong danh sách do backend quyết (`delegate_first`): **giấy ủy quyền đứng đầu**, thẻ căn cước
của cùng người chỉ dùng để **bù** field giấy ủy quyền bỏ trống (ngày sinh / giới tính / địa chỉ).

Extension chọn theo thứ tự:

| # | Phép khớp | Kết quả |
|---|---|---|
| 1 | Bản **cùng số định danh** với tài khoản **và** họ tên khớp luôn tên tài khoản | lấy bản đó |
| 2 | Cùng số định danh nhưng **không bản nào khớp tên** | **gộp** các bản (bản đứng trước thắng) — tránh mất ngày sinh/địa chỉ mà chỉ một bản có |
| 3 | Không bản nào khớp số → khớp **họ tên**, với điều kiện số định danh không mâu thuẫn | lấy bản đó |
| 4 | Trùng tên nhưng số định danh **khác** tài khoản | `null` + cảnh báo — coi là người khác |
| 5 | Form chưa có tên lẫn số (chưa bấm "Sao chép tài khoản") | `null` |

### Họ tên luôn ghi theo TÀI KHOẢN

`buildSubmitterOverride()` thay `hoTen` bằng tên đọc thô từ form tài khoản, kể cả khi đã khớp.

Lý do: phép so tên (`foldBusinessPageText`) **bỏ dấu**, nên "Vũ Đình Thiệt" ≡ "Vũ Đình Thiết" — không
thể dùng nó để phát hiện OCR sai dấu, mà giấy ủy quyền viết tay lại rất hay sai dấu. Cổng chỉ nhận
nhân thân trùng tài khoản đang đăng nhập; ghi tên lệch vào thì sau khi Lưu bị đẩy ngược về dữ liệu
tài khoản. Hồ sơ chỉ còn nhiệm vụ cấp ngày sinh / giới tính / địa chỉ.

---

## 5. Địa chỉ người nộp — quy tắc riêng

`submitterAddressFields()` không suy vai trò từ radio khi caller đã đối chiếu (nhánh Đà Nẵng ép radio
nên radio không còn nói lên ai là người nộp).

| Tài khoản | Địa chỉ điền |
|---|---|
| **Là** chủ hộ | địa chỉ cá nhân trong Giấy đề nghị (`__applicantAddress.self`) |
| **Khác** chủ hộ, có nhân thân khớp | địa chỉ trên CCCD của chính người đăng nhập |
| **Khác** chủ hộ, không khớp ai | **để trống** — thà trống còn hơn ghi địa chỉ chủ hộ vào người nộp |

---

## 6. Bảng tổng hợp

| Thủ tục | Tài khoản vs chủ hộ | Tỉnh tài khoản | Tick ủy quyền? | Ghi nhân thân? | Địa chỉ |
|---|---|---|---|---|---|
| Đăng ký thành lập | trùng | bất kỳ | Không | Không | trong đơn |
| Đăng ký thành lập | khác | ≠ Đà Nẵng | **Có** | Có, nếu khớp nhân thân | CCCD người nộp |
| Đăng ký thành lập | khác | Đà Nẵng | **Không** (ép) | **Không** | CCCD người nộp |
| Chấm dứt hoạt động | khác | ≠ Đà Nẵng | **Có** | Có, nếu khớp nhân thân | CCCD người nộp |
| Chấm dứt hoạt động | khác | Đà Nẵng | **Không** (ép) | **Không** | CCCD người nộp |
| Thay đổi nội dung | khác | kể cả Đà Nẵng | **Có** | Có, nếu khớp nhân thân | CCCD người nộp |
| Cấp lại / cấp đổi GCN | khác | kể cả Đà Nẵng | **Có** | Có, nếu khớp nhân thân | CCCD người nộp |
| Bất kỳ | hồ sơ không có nhân thân chủ hộ | bất kỳ | **Không đụng** | theo radio đang tick | theo radio |

---

## 7. Log để soi khi chạy thật

Mỗi lượt vào trang Người nộp đều in trạng thái đầu vào:

```
[FillAll] vai trò người nộp — businessDefaults: {...} | workflow: create | ép Người có thẩm quyền ký: false
```

Các dòng đáng chú ý khác:

| Log | Ý nghĩa |
|---|---|
| `tài khoản khác chủ hộ (cả số và tên) → chọn Người được ủy quyền` | vừa tick ủy quyền |
| `tài khoản khớp chủ hộ (...) → Người có thẩm quyền ký` | tick về chủ hộ |
| `hồ sơ không có nhân thân chủ hộ để đối chiếu → giữ nguyên vai trò đang tick` | `ownerUnknown` |
| `tài khoản Đà Nẵng → giữ nguyên / tick lại Người có thẩm quyền ký` | nhánh ép |
| `người nộp = CCCD khớp tài khoản: <tên> <số>` | đã chọn được nhân thân |
| `nhân thân khớp số định danh nhưng LỆCH TÊN tài khoản` | nghi OCR sai tên, sẽ ghi tên theo tài khoản |
| `hồ sơ không có CCCD nào khớp người đăng nhập → giữ nguyên dữ liệu tài khoản` | không ghi đè |
| `người được ủy quyền: <field> = <giá trị>` | từng field vừa ghi |

---

## 8. Test bao phủ

| File | Bao phủ |
|---|---|
| [`tests/business-danang-submitter-role.test.js`](../tests/business-danang-submitter-role.test.js) | ngoại lệ Đà Nẵng: thủ tục nào được ép, tick radio, địa chỉ không kéo của chủ hộ |
| [`tests/business-submitter-name-match.test.js`](../tests/business-submitter-name-match.test.js) | chọn nhân thân theo tên tài khoản, gộp khi cả hai bản sai tên, ghi tên theo tài khoản |
| `auto-fill-hcc-backend/tests/unit/test_dang_ky_kinh_doanh_mapper.py` | thứ tự ưu tiên giấy ủy quyền → CCCD trong `__identityCandidates` |
| `auto-fill-hcc-backend/tests/unit/test_cham_dut_hoat_dong_ho_kinh_doanh.py` | cùng quy tắc ưu tiên ở luồng chấm dứt |
