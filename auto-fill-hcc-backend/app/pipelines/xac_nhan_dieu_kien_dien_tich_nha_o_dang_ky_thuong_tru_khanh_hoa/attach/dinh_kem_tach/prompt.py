"""Prompt chia trang thành từng giấy khi TÁCH đính kèm xác nhận điều kiện diện tích nhà ở để đăng ký thường trú (1.013314,
cổng Khánh Hòa)."""

import json
from typing import Any

from ..dinh_kem_khong_tach.prompt import DOC_TYPE_DEFINITIONS

SYSTEM_PROMPT = f"""
<persona>
Bạn chia bộ hồ sơ scan của thủ tục "Xác nhận về điều kiện diện tích bình quân nhà ở để đăng ký thường trú vào chỗ ở do thuê,
mượn, ở nhờ" (cổng dịch vụ công tỉnh Khánh Hòa) thành từng GIẤY TỜ riêng và gán loại cho từng giấy. Mỗi tệp gồm các trang
theo thứ tự, mỗi trang kèm chữ OCR (phần đầu trang).
</persona>

<rules>
1. Trang 1 của mỗi tệp luôn mở một giấy.
2. Một trang MỞ GIẤY MỚI khi nó là trang đầu của một văn bản KHÁC giấy trước: có quốc hiệu/tiêu đề riêng (tờ khai, Giấy
   chứng nhận, hợp đồng, giấy ủy quyền...), là thẻ CCCD, hoặc cùng loại nhưng khác người/khác số hiệu.
3. KHÔNG mở giấy mới cho trang nối tiếp của cùng văn bản: trang 2 của Tờ khai Mẫu 02 (ngày ký, "Người đề nghị", "XÁC NHẬN
   CỦA UBND", chú thích), trang "Sơ đồ thửa đất" / "Những thay đổi sau khi cấp" của Giấy chứng nhận, các trang điều khoản
   của hợp đồng, trang "Lời chứng chứng thực chữ ký" in sau giấy ủy quyền, mặt sau thẻ. Mặt trước + mặt sau CCCD của CÙNG
   một người là MỘT giấy.
4. Trang trắng hoặc không đọc được thuộc giấy liền trước. Không chắc → KHÔNG tách.
5. Tệp chỉ có 1 trang mà chữ cho thấy nhiều giấy (bản gộp không tách được trang) → liệt kê đủ các giấy, trangDau đều là 1.
6. Chỉ dùng chữ OCR, không dùng tên tệp. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</rules>

{DOC_TYPE_DEFINITIONS}

<ten>
"ten": tên tiếng Việt ngắn gọn (tối đa khoảng 60 ký tự) theo tiêu đề giấy, dùng làm tên tệp khi đính: "Tờ khai xác nhận
tình trạng chỗ ở hợp pháp", "Giấy chứng nhận quyền sử dụng đất", "Hợp đồng thuê nhà ở", "Căn cước công dân". Không ghi họ
tên, số giấy tờ. OCR quá thiếu → để trống.
</ten>

<output_contract>
{{"tep":[{{"fileIndex":0,"giayTo":[{{"trangDau":1,"docType":"to_khai","ten":"Tờ khai xác nhận tình trạng chỗ ở hợp pháp"}},{{"trangDau":3,"docType":"identity","ten":"Căn cước công dân"}}]}}]}}
Mỗi tệp đầu vào đúng một phần tử "tep"; "giayTo" xếp theo trangDau tăng dần.
</output_contract>
""".strip()


def build_user_prompt(files: list[dict[str, Any]]) -> str:
    total = sum(len(item.get("trang") or []) for item in files)
    return ("HỒ SƠ:\n" + json.dumps(files, ensure_ascii=False)
            + f"\n\nHồ sơ có {len(files)} tệp, tổng {total} trang. Chia giấy tờ cho từng tệp.")
