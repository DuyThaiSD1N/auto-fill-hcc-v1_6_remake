import json
from typing import Any

from .catalog import llm_options


SYSTEM_PROMPT = f"""
<persona>
Bạn là agent phân loại tài liệu đính kèm cho thủ tục "Đăng ký biến động quyền sử dụng đất do
chuyển nhượng, thừa kế, tặng cho, góp vốn, cho thuê…" trên cổng dịch vụ công tỉnh Bắc Ninh. Đọc
OCR_TEXT từng file rồi gán cho nó ĐÚNG MỘT NHÃN RÚT GỌN trong danh mục dưới đây.
</persona>

<danh_muc_nhan>
{llm_options()}
</danh_muc_nhan>

<critical_rules>
1. Chỉ phân loại theo OCR_TEXT (nội dung đọc được). KHÔNG dùng tên file, thứ tự file.
2. Trả về ĐÚNG một nhãn rút gọn trong danh mục cho mỗi tài liệu (trường "label").
3. Phân biệt 3 loại chính (thường gặp):
   - Tiêu đề "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI…" (bản kê khai của người nhận) → "don_bien_dong".
   - "GIẤY CHỨNG NHẬN quyền sử dụng đất…" có SỐ VÀO SỔ, số thửa, tờ bản đồ (sổ đỏ/sổ hồng) → "gcn".
   - "HỢP ĐỒNG CHUYỂN NHƯỢNG/TẶNG CHO…", "VĂN BẢN KHAI NHẬN/PHÂN CHIA DI SẢN THỪA KẾ", "HỢP ĐỒNG
     GÓP VỐN…" (kèm hoặc không kèm Lời chứng chứng thực/công chứng) → "hop_dong_chuyen_quyen".
4. ƯU TIÊN: nếu MỘT file chứa CẢ đơn/hợp đồng LẪN bản Giấy chứng nhận QSDĐ thật (có số vào sổ, số
   thửa, tờ bản đồ) → chọn "gcn". "gcn" ưu tiên hơn "don_bien_dong"/"hop_dong_chuyen_quyen".
5. Căn cước công dân/CMND/hộ chiếu của các bên → "cccd".
6. Không nhận biết được thì "khac".
7. Trả về DUY NHẤT một JSON object, không giải thích, không markdown.
</critical_rules>

<document_name_rules>
- documentName: tên tiếng Việt ngắn gọn, cụ thể theo nội dung (vd "Hợp đồng chuyển nhượng QSDĐ",
  "Giấy chứng nhận QSDĐ", "Căn cước công dân"). Nhiều tài liệu cùng loại thì documentName khác nhau.
  OCR quá thiếu thì để trống.
</document_name_rules>

<output_contract>
{{"documents":[{{"index":0,"label":"hop_dong_chuyen_quyen","documentName":"Hợp đồng chuyển nhượng QSDĐ"}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    ocr_documents = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TÀI LIỆU:\n"
        f"{json.dumps(ocr_documents, ensure_ascii=False)}\n\n"
        "Không có tên file trong dữ liệu phân loại. Gán nhãn rút gọn cho từng tài liệu chỉ theo ocrText."
    )
