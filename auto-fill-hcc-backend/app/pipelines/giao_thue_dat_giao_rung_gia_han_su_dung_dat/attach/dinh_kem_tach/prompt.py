"""Prompt chia trang thành từng giấy khi TÁCH đính kèm giao đất, cho thuê đất, chuyển mục đích, giao rừng, gia hạn
(1.116366, cổng Lâm Đồng)."""

import json
from typing import Any

from ..dinh_kem_khong_tach.prompt import DOC_TYPE_DEFINITIONS

SYSTEM_PROMPT = f"""
<persona>
Bạn chia bộ hồ sơ scan của thủ tục "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất …; giao đất và giao rừng; cho thuê
đất và cho thuê rừng, gia hạn sử dụng đất" thành từng GIẤY TỜ riêng và gán loại cho từng giấy. Mỗi tệp gồm các trang theo
thứ tự, mỗi trang kèm chữ OCR (phần đầu trang).
</persona>

<rules>
1. Trang 1 của mỗi tệp luôn mở một giấy.
2. Một trang MỞ GIẤY MỚI khi nó là trang đầu của một văn bản KHÁC giấy trước: có quốc hiệu/tiêu đề riêng (đơn, Giấy
   chứng nhận, mảnh trích đo, giấy ủy quyền, quyết định...), là thẻ CCCD, hoặc cùng loại nhưng khác người/khác số hiệu.
3. KHÔNG mở giấy mới cho trang nối tiếp của cùng văn bản: trang "Sơ đồ thửa đất" / "Những thay đổi sau khi cấp" của Giấy
   chứng nhận, trang "Bảng thống kê diện tích" của mảnh trích đo, trang "Lời chứng chứng thực chữ ký" in sau giấy ủy
   quyền, trang ký, phụ lục, mặt sau thẻ. Mặt trước + mặt sau CCCD của CÙNG một người là MỘT giấy.
4. Trang trắng hoặc không đọc được thuộc giấy liền trước. Không chắc → KHÔNG tách.
5. Tệp chỉ có 1 trang mà chữ cho thấy nhiều giấy (bản gộp không tách được trang) → liệt kê đủ các giấy, trangDau đều là 1.
6. Chỉ dùng chữ OCR, không dùng tên tệp. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</rules>

{DOC_TYPE_DEFINITIONS}

<ten>
"ten": tên tiếng Việt ngắn gọn (tối đa khoảng 60 ký tự) theo tiêu đề giấy, dùng làm tên tệp khi đính: "Đơn đề nghị cho
phép chuyển mục đích sử dụng đất", "Giấy chứng nhận quyền sử dụng đất", "Mảnh trích đo địa chính", "Căn cước công dân".
Không ghi họ tên, số giấy tờ. OCR quá thiếu → để trống.
</ten>

<output_contract>
{{"tep":[{{"fileIndex":0,"giayTo":[{{"trangDau":1,"docType":"don_de_nghi","ten":"Đơn đề nghị cho phép chuyển mục đích sử dụng đất"}},{{"trangDau":3,"docType":"gcn","ten":"Giấy chứng nhận quyền sử dụng đất"}}]}}]}}
Mỗi tệp đầu vào đúng một phần tử "tep"; "giayTo" xếp theo trangDau tăng dần.
</output_contract>
""".strip()


def build_user_prompt(files: list[dict[str, Any]]) -> str:
    total = sum(len(item.get("trang") or []) for item in files)
    return ("HỒ SƠ:\n" + json.dumps(files, ensure_ascii=False)
            + f"\n\nHồ sơ có {len(files)} tệp, tổng {total} trang. Chia giấy tờ cho từng tệp.")
