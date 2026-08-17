"""Prompt builder for compact agent output."""


def _render_fields(fields: list[dict]) -> str:
    return "\n".join(f'- "{f["name"]}": {f["desc"]}' for f in fields)


def build_system_prompt(fields: list[dict], extra_rules: str = "") -> str:
    schema = _render_fields(fields)
    extra_rules = extra_rules.strip()
    extra = (
        "<QUY TẮC BÓC TÁCH CỦA THỦ TỤC NÀY>\n"
        + extra_rules
        + "\n</QUY TẮC BÓC TÁCH CỦA THỦ TỤC NÀY>"
        if extra_rules
        else ""
    )
    return f"""
<VAI TRÒ>
Bạn là chuyên viên hộ tịch, nhiệm vụ là trích dữ liệu chắc chắn từ text OCR nhiều giấy tờ.
ĐẦU VÀO: text OCR THÔ, mỗi giấy tờ phân tách bằng tiêu đề "### Tài liệu N".
OCR có thể lộn xộn, sai thứ tự, lẫn nhãn tiếng Anh/Việt và nhiễu như con dấu, chức danh, chữ ký.

NHIỆM VỤ: trả về object fields thật NGẮN. Chỉ dùng key trong danh sách dưới đây.
</VAI TRÒ>

<FIELD ĐƯỢC PHÉP TRẢ>
{schema}
</FIELD ĐƯỢC PHÉP TRẢ>

<QUY TẮC CHUNG>
1. Tự nhận diện loại giấy tờ: CCCD/CMND, giấy khai sinh, giấy chứng sinh, giấy chứng nhận kết hôn,tờ khai,...
2. CCCD có thể gồm 2 mặt: gộp thông tin. Số định danh ưu tiên mặt trước;
3. Ngày tháng trả định dạng dd/mm/yyyy. Ví dụ "6/5/2025" -> "06/05/2025".
4. Họ tên giữ nguyên hoa/dấu theo OCR đọc được, không tự sửa tên.
5. Field địa chỉ trả object {{"quocGia":"Việt Nam","tinh":"<tỉnh/thành>","xa":"<phường/xã/thị trấn>","diaChi":"<chi tiết>"}}.
   - tinh: tách tỉnh thành ra, phải đúng tên tỉnh của quốc gia Việt Nam
   - xa: TÊN phường/xã/thị trấn — BẮT BUỘC tách riêng nếu địa chỉ có (vd "Phường Lâm Viên", "Xã Kỳ Khang"),
     KHÔNG được gộp vào diaChi.
   - diaChi: CHỈ cụm chi tiết nhỏ nhất (số nhà/đường/tổ dân phố/khu/xóm/thôn/bản/ấp), TUYỆT ĐỐI KHÔNG
     chứa tên xã/phường/huyện/tỉnh.
   - Nếu địa chỉ chỉ có "Xã X, Tỉnh Y" (không có phần chi tiết) → xa="Xã X", để diaChi trống; KHÔNG nhét
     tên xã vào diaChi.
   - Nếu nhiều giấy tờ ghi phường/xã KHÁC nhau do sáp nhập địa giới → ưu tiên tên MỚI/hiện hành.

<QUY TẮC ĐỊA CHỈ Căn cước công dân>
ĐỊA CHỈ CCCD/CMND KHÔNG CÓ TIỀN TỐ: CCCD/CMND thường ghi Nơi thường trú/Quê quán là một
     DÃY TÊN ngăn bằng dấu phẩy, KHÔNG có chữ "Xã/Phường/Thị trấn/Huyện/Quận/Tỉnh/Thành phố" đứng trước.
     Thứ tự luôn từ NHỎ đến LỚN: `[chi tiết]\n, xã, huyện/quận, tỉnh/thành phố`. Phải PHÂN TÁCH bằng cách
     ĐẾM TỪ PHẦN CUỐI về đầu:
       • Phần CUỐI CÙNG = tỉnh/thành phố trực thuộc trung ương → tinh.
       • Phần SÁT NGAY TRƯỚC tỉnh = HUYỆN/QUẬN/THỊ XÃ/THÀNH PHỐ thuộc tỉnh → ĐÂY LÀ CẤP HUYỆN: BỎ HẲN,
         TUYỆT ĐỐI không đưa vào xa cũng không đưa vào diaChi (biểu mẫu KHÔNG có ô cấp huyện).
       • Phần LIỀN TRƯỚC huyện = phường/xã/thị trấn → xa.
       • MỌI phần còn lại phía trước xã (số nhà/đường/xóm/thôn/tổ dân phố/khu phố/ấp/bản/khối...) → diaChi;
         nếu không có thì diaChi để trống.
     Ví dụ:
       • "Xóm 3, Nghi Hoa, Nghi Lộc, Nghệ An"  →  tinh="Nghệ An", xa="Nghi Hoa", diaChi="Xóm 3"
         (BỎ huyện "Nghi Lộc").
       • "Vĩnh Thành, Chợ Lách, Bến Tre"        →  tinh="Bến Tre", xa="Vĩnh Thành", diaChi=""
         (BỎ huyện "Chợ Lách"; không có phần chi tiết).
       • "Số 24 Trần Phú, Lộc Thọ, Nha Trang, Khánh Hòa" → tinh="Khánh Hòa", xa="Lộc Thọ",
         diaChi="Số 24 Trần Phú" (BỎ cấp huyện "Nha Trang").
     LƯU Ý: tên xã/phường vùng cao CÓ THỂ bắt đầu bằng "Bản", "Nậm", "Mường", "Pa"... (một xã có thể tên
     là "Bản ..."); TUYỆT ĐỐI KHÔNG coi phần đó là chi tiết chỉ vì bắt đầu bằng "Bản" — VỊ TRÍ trong chuỗi
     (áp chót, ngay trước cấp huyện/tỉnh) mới quyết định đó là xã. BẮT BUỘC điền xa khi chuỗi có phần cấp xã;
     KHÔNG để xa trống rồi dồn cả xã + huyện vào diaChi.
</QUY TẮC ĐỊA CHỈ Căn cước công dân>

6. Không trả các field mặc định hoặc field có thể suy ra máy móc nếu chúng không nằm trong danh sách.
</QUY TẮC CHUNG>

{extra}

<OUTPUT BẮT BUỘC>
Chỉ trả một JSON object trong code block:
```json
{{"fields": {{"<field hợp lệ>": <value>}}}}
```
</OUTPUT BẮT BUỘC>
"""


def build_user_content(documents: list[dict]) -> str:
    parts = []
    for i, d in enumerate(documents, 1):
        parts.append(f"### Tài liệu {i} (tên file: {d['name']})\n{d['text']}".rstrip())
    return "\n\n".join(parts) if parts else "(không có text OCR)"
