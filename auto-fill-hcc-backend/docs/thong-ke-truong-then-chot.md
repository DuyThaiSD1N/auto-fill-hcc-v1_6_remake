# Thống kê "trường then chốt" theo từng thủ tục auto-fill

> Dùng làm cột **Tổng trường then chốt** (mẫu sheet chấm điểm auto-fill). Số này là mốc mặc định;
> mỗi hồ sơ cụ thể có thể lệch vì phụ thuộc giấy tờ thực sự tải lên (vd không có cha/mẹ, không có
> giấy chứng nhận…).

## Định nghĩa "trường then chốt"
Trường **thông tin lấy từ giấy tờ** (OCR/LLM) mà **sai thì hồ sơ sai**. Đếm mỗi thông tin **một lần**.

**KHÔNG tính** (không phải then chốt):
- **Mặc định / bôi vàng**: loại cư trú ("Thường trú"), radio nơi cư trú (trong/ngoài nước), quốc tịch mặc định "Việt Nam", loại giấy tờ tùy thân ("Căn cước công dân"), loại đăng ký, nghiệp vụ đăng ký, phương thức nhận kết quả, đề nghị cấp bản sao/số lượng.
- **Trùng lặp**: "Số giấy tờ tùy thân" = "Số định danh" (chỉ đếm 1).
- **Mã hoá nội bộ**: MaDanToc/MaQuocGia/MaQuocTich (là mã của trường đã đếm).
- **Cư trú**: đếm phần **địa danh** (tỉnh/xã/địa chỉ) là **1** trường, không tách radio.

**Lưu ý người yêu cầu**: các form moj (khai tử, trích lục, TTHN, thay đổi hộ tịch) thường được cổng
**điền sẵn người yêu cầu từ VNeID**; ta vẫn auto-fill/đối chiếu nên **vẫn tính** vào then chốt (đánh dấu ⓝ).

---

## Bảng tổng hợp

| Thủ tục | Số trường then chốt |
| --- | :---: |
| Đăng ký kết hôn | **14** |
| Đăng ký khai tử | **21** |
| Đăng ký khai sinh (thường) | **26** |
| Đăng ký lại khai sinh | **30** |
| Liên thông khai sinh | **16** |
| Thay đổi/cải chính hộ tịch | **13** |
| Cấp bản sao trích lục / GKS | **18** |
| Xác nhận tình trạng hôn nhân | **15** |
| Đính chính GCN đã cấp | **12** |
| Điều chỉnh QĐ giao/thuê đất | **12** |
| Đăng ký đất đai lần đầu (tổ chức) | **12** |
| Đăng ký đất đai lần đầu (hộ/cá nhân/gốc VN ở NN) | **12** |
| Hỗ trợ chi phí mai táng | **16** (8 nếu người nộp = chủ hồ sơ) |
| Đăng ký hộ kinh doanh | **15** |

---

## Chi tiết từng thủ tục

### Đăng ký kết hôn — 14
Bên nam (7) + Bên nữ (7), mỗi bên: Họ tên · Ngày sinh · Dân tộc · Số định danh · Ngày cấp · Nơi cấp · Nơi cư trú.

### Đăng ký khai tử — 21
- Người yêu cầu ⓝ (5): Họ tên · Số định danh · Ngày cấp · Nơi cấp · Nơi cư trú
- Người mất (9): Họ tên · Ngày sinh · Giới tính · Dân tộc · Số định danh · Ngày cấp · Nơi cấp · Nơi cư trú · Nơi chết
- Sự kiện chết (4): Ngày mất · Giờ · Phút · Nguyên nhân
- Giấy báo tử (3): Số · Cơ quan cấp · Ngày cấp

### Đăng ký khai sinh (thường) — 26
- Người yêu cầu (6): Họ tên · Số định danh · Ngày cấp · Nơi cấp · Nơi cư trú · Quan hệ với người được khai sinh
- Con (6): Họ tên · Ngày sinh · Giới tính · Dân tộc · Nơi sinh · Quê quán
- Cha (7): Họ tên · Năm sinh · Dân tộc · Số định danh · Ngày cấp · Nơi cấp · Nơi cư trú
- Mẹ (7): như Cha

### Đăng ký lại khai sinh — 30
= Đăng ký khai sinh thường (26) + **Hồ sơ gốc (4)**: Số · Quyển số · Ngày đăng ký · Cơ quan đăng ký trước đây.

### Liên thông khai sinh — 16
- Con (4): Ngày sinh · Giới tính · Nơi sinh · Quê quán
- Cha (4): Họ tên · Ngày sinh · Số giấy tờ · Địa chỉ cư trú
- Mẹ (3): Ngày sinh · Số giấy tờ · Địa chỉ cư trú *(form liên thông không có ô "họ tên mẹ" riêng)*
- Giấy CN kết hôn (4): Số · Quyển số · Ngày cấp · Nơi cấp
- Liên hệ (1): SĐT người yêu cầu

### Thay đổi / cải chính / bổ sung hộ tịch — 13
- Người yêu cầu ⓝ (1): Số giấy tờ tùy thân (cổng điền sẵn tên/số định danh)
- Người có nội dung thay đổi (8): Họ tên · Ngày sinh · Giới tính · Dân tộc · Số định danh · Ngày cấp GT · Nơi cấp GT · Nơi cư trú
- Hồ sơ gốc (4): Số · Quyển số · Ngày đăng ký · Nơi đăng ký

### Cấp bản sao trích lục / Giấy khai sinh — 18
- Người yêu cầu ⓝ (5): Họ tên · Số định danh · Ngày cấp · Nơi cấp · Nơi cư trú
- Người được đăng ký (8): Họ tên · Ngày sinh · Giới tính · Dân tộc · Số định danh · Ngày cấp · Nơi cấp · Nơi cư trú
- Hồ sơ hộ tịch (5): Tên loại giấy tờ · Cơ quan đăng ký · Số · Quyển số · Ngày đăng ký

### Xác nhận tình trạng hôn nhân — 15
- Người yêu cầu ⓝ (5): Họ tên · Số định danh · Ngày cấp · Nơi cấp · Nơi cư trú
- Người được xác minh (9): Họ tên · Ngày sinh · Giới tính · Dân tộc · Số định danh · Ngày cấp · Nơi cấp · Nơi cư trú · Tình trạng hôn nhân
- Quan hệ với người được xác minh (1)

### Đính chính GCN / Điều chỉnh QĐ đất / Đăng ký đất đai lần đầu (×2) — 12 mỗi thủ tục
*(Cùng bộ trường `CongDan_*`)*
- Người nộp (7): Họ tên · Ngày sinh · Giới tính · Dân tộc · Số CCCD · Ngày cấp · Nơi cấp
- Tổ chức (2): Tên cơ quan/tổ chức · Mã số thuế người nộp
- Giấy chứng nhận/giấy phép (3): Số · Ngày cấp · Nơi cấp

### Hỗ trợ chi phí mai táng — 16 (hoặc 8)
- Người nộp hồ sơ (8): Họ tên · Ngày sinh · Giới tính · Số định danh · Ngày cấp · Nơi cấp · Địa chỉ · Tỉnh/Xã
- Chủ hồ sơ (8): như trên *(chỉ khi người nộp ≠ chủ hồ sơ; nếu trùng → 8)*

### Đăng ký hộ kinh doanh — 15
- Hộ kinh doanh (4): Tên hộ KD · Tên viết tắt · Ngành nghề · Vốn điều lệ
- Chủ hộ (6): Họ tên · Ngày sinh · Giới tính · Số giấy tờ · SĐT · Email
- Thuế (2): Phương pháp tính thuế · Số lao động
- Địa chỉ trụ sở (3): Tỉnh · Xã/Phường · Địa chỉ chi tiết

---

> **Nguồn sự thật (code):** danh sách trường then chốt được mã hoá tại `app/traces/key_fields.py`
> (`KEY_FIELDS_BY_PROCEDURE`). Trace realtime và script Excel đều dùng chung file này — sửa số ở đó.

## Ghi chú áp dụng
- Con số là **tối đa khi có đủ giấy tờ**. Nếu hồ sơ thiếu 1 nhóm (vd chỉ có cha, không có mẹ) → trừ số trường của nhóm đó khỏi "Tổng trường then chốt" của hồ sơ.
- Trường **người yêu cầu (ⓝ)**: nếu bạn coi cổng đã tự điền (không tính vào chấm auto-fill), trừ phần ⓝ ra khỏi tổng.
- Danh sách/định nghĩa có thể chỉnh — cho tôi biết muốn siết/nới nhóm nào để cập nhật lại số.
