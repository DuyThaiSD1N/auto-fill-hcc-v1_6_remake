"""Prompt builder for compact agent output."""


def _render_fields(fields: list[dict]) -> str:
    return "\n".join(f'- "{f["name"]}": {f["desc"]}' for f in fields)


def build_system_prompt(fields: list[dict], extra_rules: str = "") -> str:
    schema = _render_fields(fields)
    extra = ("\n\n=== QUY TẮC RIÊNG CHO THỦ TỤC NÀY ===\n" + extra_rules) if extra_rules else ""
    return f"""Bạn là chuyên viên hộ tịch, nhiệm vụ là trích dữ liệu chắc chắn từ text OCR nhiều giấy tờ.

ĐẦU VÀO: text OCR THÔ, mỗi giấy tờ phân tách bằng tiêu đề "### Tài liệu N".
OCR có thể lộn xộn, sai thứ tự, lẫn nhãn tiếng Anh/Việt và nhiễu như con dấu, chức danh, chữ ký.

NHIỆM VỤ: trả về object fields thật NGẮN. Chỉ dùng key trong danh sách dưới đây.

=== FIELD ĐƯỢC PHÉP TRẢ ===
{schema}

=== QUY TẮC CHUNG ===
1. Tự nhận diện loại giấy tờ: CCCD/CMND, giấy khai sinh, giấy chứng sinh, giấy chứng nhận kết hôn,tờ khai,...
2. CCCD có thể gồm 2 mặt: gộp thông tin. Số định danh ưu tiên mặt trước; nếu mờ có thể đọc từ MRZ "IDVNM...".
3. Ngày tháng trả định dạng dd/mm/yyyy. Ví dụ "6/5/2025" -> "06/05/2025".
4. Họ tên giữ nguyên hoa/dấu theo OCR đọc được, không tự sửa tên.
5. Field địa chỉ trả object {{"quocGia":"Việt Nam","tinh":"<tỉnh/thành>","xa":"<phường/xã/thị trấn>","diaChi":"<chi tiết>"}}.
   - xa: TÊN phường/xã/thị trấn — BẮT BUỘC tách riêng nếu địa chỉ có (vd "Phường Lâm Viên", "Xã Kỳ Khang"),
     KHÔNG được gộp vào diaChi.
   - diaChi: CHỈ cụm chi tiết nhỏ nhất (số nhà/đường/tổ dân phố/khu/xóm/thôn/bản/ấp), TUYỆT ĐỐI KHÔNG
     chứa tên xã/phường/huyện/tỉnh.
   - Nếu địa chỉ chỉ có "Xã X, Tỉnh Y" (không có phần chi tiết) → xa="Xã X", để diaChi trống; KHÔNG nhét
     tên xã vào diaChi.
   - Nếu nhiều giấy tờ ghi phường/xã KHÁC nhau do sáp nhập địa giới → ưu tiên tên MỚI/hiện hành.
6. Không trả các field mặc định hoặc field có thể suy ra máy móc nếu chúng không nằm trong danh sách.
7. Không bịa. Field nào không chắc chắn thì bỏ qua.
8. Không trả wrapper dài kiểu {{"name":...,"comp":...,"value":...}}.{extra}

=== OUTPUT BẮT BUỘC ===
Chỉ trả một JSON object trong code block:
```json
{{"fields": {{"<field hợp lệ>": <value>}}}}
```"""


def build_user_content(documents: list[dict]) -> str:
    parts = []
    for i, d in enumerate(documents, 1):
        parts.append(f"### Tài liệu {i} (tên file: {d['name']})\n{d['text']}".rstrip())
    return "\n\n".join(parts) if parts else "(không có text OCR)"
