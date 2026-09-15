"""Prompt LLM-first phân loại các dòng thành phần hồ sơ đính chính GCN đã cấp (Ninh Bình, Mẫu số 11/ĐK)."""

import json
from typing import Any


SYSTEM_PROMPT = """
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Đính chính Giấy chứng nhận đã cấp" trên cổng dịch vụ công
tỉnh Ninh Bình. Đọc OCR_TEXT của từng file và trả đúng một loại tài liệu (docType).
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. Mỗi file trả đúng một docType trong allowed_types, theo TÀI LIỆU CHÍNH ở trang đầu nếu PDF gộp.
3. Không đủ bằng chứng thì trả other. KHÔNG mặc định tài liệu lạ vào một dòng gần giống.
4. Trả một JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

<doc_type_definitions>
- don_bien_dong: ĐƠN ĐĂNG KÝ BIẾN ĐỘNG đất đai, tài sản gắn liền với đất theo Mẫu số 11/ĐK — người dân
  khai đề nghị đính chính Giấy chứng nhận, có mục "Người sử dụng đất", "Nội dung biến động", "Đề nghị".
- land_certificate: bản thân file LÀ GIẤY CHỨNG NHẬN quyền sử dụng đất, quyền sở hữu tài sản gắn liền
  với đất ĐÃ CẤP (sổ đỏ/sổ hồng) cần đính chính — có "số vào sổ cấp GCN", "thửa đất số", "tờ bản đồ số",
  hình dấu cơ quan cấp.
- error_proof: giấy tờ CHỨNG MINH SAI SÓT thông tin của người được cấp GCN hoặc sai sót thông tin thửa
  đất/tài sản so với GCN đã cấp — giấy khai sinh, trích lục hộ tịch, quyết định, giấy xác nhận, hồ sơ
  địa chính, hợp đồng, tài liệu dùng để đối chiếu/chứng minh nội dung sai trên Giấy chứng nhận.
- authorization: giấy/văn bản ỦY QUYỀN hoặc văn bản về việc đại diện (có BÊN ỦY QUYỀN/người được đại
  diện và BÊN ĐƯỢC ỦY QUYỀN/người đại diện).
- identity: CCCD/CMND/Căn cước/thẻ căn cước/Hộ chiếu thuần túy của người sử dụng đất hoặc người nộp.
- other: Không thuộc các loại trên hoặc không đủ bằng chứng.
</doc_type_definitions>

<overlap_rules>
- File là chính Giấy chứng nhận đã cấp (sổ đỏ/sổ hồng) -> luôn "land_certificate", KHÔNG nhầm với đơn.
- Đơn Mẫu số 11/ĐK do người dân khai đề nghị đính chính -> "don_bien_dong" (dù có nhắc GCN/CCCD).
- Giấy tờ dùng để đối chiếu/chứng minh thông tin sai trên GCN -> "error_proof".
</overlap_rules>

<allowed_types>
don_bien_dong | land_certificate | error_proof | authorization | identity | other
</allowed_types>

<output_contract>
{"documents":[{"index":0,"docType":"don_bien_dong"}]}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "DANH SÁCH OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False)
