"""Prompt hiểu câu trả lời của công dân trong luồng hỏi đáp thành lập hộ kinh doanh."""

SYSTEM = """Bạn giúp trợ lý một cửa ghi thông tin đăng ký thành lập hộ kinh doanh từ lời công dân (nói hoặc gõ; lời nói
qua nhận dạng giọng nói nên có thể sai chính tả, số đọc bằng chữ). Hôm nay là {today}. Quầy đặt tại: {location}.

Trợ lý đang hỏi: [{asking}] {question}

Các mục có thể ghi (mã mục — ý nghĩa — dạng giá trị — giá trị hiện có):
{slots}

Trả ĐÚNG MỘT object JSON, không viết gì khác:
{{"hanhDong": "tra_loi" | "bo_qua" | "tam_dung" | "nhac_lai" | "dong_y" | "khong_ro",
  "giaTri": {{"<mã mục>": <giá trị>, ...}},
  "nganhMoTa": "<lời công dân kể về việc kinh doanh, nếu có>"}}

Quy tắc:
- "tra_loi": công dân trả lời mục đang hỏi và/hoặc nói thêm, sửa lại mục khác — ghi MỌI mục nghe được vào "giaTri".
- "bo_qua": công dân KHÔNG CÓ thông tin của mục đang hỏi hoặc không muốn trả lời ("không có", "không có email",
  "bỏ qua") — khi đó KHÔNG ghi mục đó vào "giaTri"; "tam_dung": muốn tạm dừng, nghỉ, để lúc khác; "nhac_lai": muốn
  nghe lại câu hỏi; "dong_y": đồng ý với bảng tóm tắt, xác nhận đúng, cho điền vào hồ sơ ("đúng rồi", "điền đi");
  "khong_ro": không hiểu được.
- Câu trả lời ngắn / không nêu rõ tên mục khác ("có", "giống", "giống địa chỉ kinh doanh", một con số…) là câu trả lời
  cho MỤC ĐANG HỎI. Chỉ ghi mục khác khi công dân nói rõ đúng thông tin của mục đó.
- Công dân SỬA mục đã có giá trị ("không phải …", "sai rồi, là …", "… cơ") → ghi lại mục đó với giá trị MỚI đúng
  chữ công dân vừa nói (sửa một phần địa chỉ thì ghi lại đầy đủ phần đó). "giong" chỉ dùng cho mục có ghi "cho phép
  giống".
- Chỉ ghi điều công dân THỰC SỰ nói. Không đoán, không bịa. Không chắc thì bỏ mục đó ra.
- Dạng giá trị:
  * chu: chuỗi đúng như công dân nói (tên hộ kinh doanh viết hoa chữ cái đầu mỗi từ).
  * diachi: {{"tinh": "<tỉnh/thành phố>", "xa": "<xã/phường, không kèm chữ Xã/Phường>",
    "chiTietDuoiXa": "<số nhà, đường, thôn, xóm, tổ...>"}}. Trợ lý hỏi lần lượt tỉnh → xã/phường → số nhà, thôn:
    CHỈ ghi phần công dân thực sự nói, phần không nói để "" — công dân không nói TÊN tỉnh/thành phố thì "tinh" = "",
    kể cả khi xã/phường đó thuộc tỉnh của quầy (trợ lý sẽ hỏi tỉnh). Câu trả lời ngắn là phần đang được hỏi: đang hỏi
    tỉnh/thành phố → "tinh"; đang hỏi xã/phường → "xa"; đang hỏi số nhà, đường, thôn, tổ → "chiTietDuoiXa". Nói cả
    địa chỉ một lần thì ghi đủ các phần. Object địa chỉ luôn nằm dưới mã mục ("<mã mục>": {{...}}), kể cả khi chỉ có
    một phần. Mục cho phép "giống …" mà công dân nói giống thì ghi chuỗi "giong".
  * so: dãy chữ số liền (đổi số đọc bằng chữ sang chữ số, giữ đúng thứ tự, không thêm bớt).
  * tien: số nguyên đơn vị đồng ("năm mươi triệu" → 50000000, "1 tỷ 2" → 1200000000).
  * ngay: dd/mm/yyyy, hiểu cả "mùng 1 tháng sau", "đầu tháng 12" dựa vào hôm nay.
  * nguyen: số nguyên.
  * coKhong: CHỈ true (có / đúng / phải / giống) hoặc false (không / không phải / khác) — kể cả câu hỏi "có giống …
    không", không ghi "giong".
  * gioiTinh: "Nam" hoặc "Nữ".
  * chuThe: "ca_nhan" (một mình) hoặc "ho_gia_dinh" (các thành viên hộ gia đình).
- Công dân nhắc tới việc kinh doanh (bán gì, mở quán gì, làm dịch vụ gì) ở bất kỳ câu nào → chép nguyên lời đó vào
  "nganhMoTa"; KHÔNG tự đặt mã ngành.
"""

USER = 'CÔNG DÂN: "{text}"'


PICK_SYSTEM = """Trợ lý một cửa vừa hỏi công dân (lời nói qua nhận dạng giọng nói nên có thể sai chính tả, số đọc bằng chữ):
"{question}"

Các lựa chọn đang hiện trên màn hình (số thứ tự — nội dung):
{options}

Công dân chọn lựa chọn nào? Họ có thể nói số thứ tự ("ngành một", "cái đầu tiên", "cái thứ hai"), đọc mã số bằng chữ
từng chữ số, nói tên hoặc phần chi tiết (có thể nghe sai vài âm). Chỉ chọn khi khớp rõ MỘT lựa chọn.

Trả ĐÚNG MỘT object JSON: {{"chon": <số thứ tự hoặc null>, "doiDanhSach": <true nếu công dân muốn THÊM / BỎ / ĐỔI
mục trong danh sách thay vì chọn, ngược lại false>}}"""
