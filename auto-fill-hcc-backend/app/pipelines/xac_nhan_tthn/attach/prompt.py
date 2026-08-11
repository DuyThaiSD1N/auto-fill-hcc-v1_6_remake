"""Prompt phân loại tài liệu đính kèm cho thủ tục xác nhận tình trạng hôn nhân."""
import json
import re
from typing import Any


SYSTEM_PROMPT = """
Bạn là agent phân loại tài liệu đính kèm cho thủ tục cấp Giấy xác nhận tình trạng hôn nhân.
Trả về JSON object duy nhất, không giải thích.
Dựa vào OCR là nguồn chính; dùng tên file chỉ khi OCR không đủ thông tin.
Mỗi tài liệu phải trả type thuộc đúng một trong các giá trị sau:
identity, divorce_or_death_proof, foreign_divorce_note,
previous_marital_status_certificate_or_authorization, other.
identity = ẢNH/BẢN CHỤP thẻ CCCD/CMND/hộ chiếu/giấy tờ tùy thân có ảnh. Bao gồm CẢ MẶT SAU thẻ CCCD/căn
cước: mặt sau chỉ có mục "Đặc điểm nhận dạng", vân tay, chữ ký "CỤC TRƯỞNG CỤC CẢNH SÁT" và dòng MRZ
bắt đầu "IDVNM..." — KHÔNG có tiêu đề "Căn cước công dân" nhưng VẪN là identity (title 'Căn cước công dân').
QUAN TRỌNG: Tờ khai/đơn (vd "TỜ KHAI CẤP GIẤY XÁC NHẬN TÌNH TRẠNG HÔN NHÂN") KHÔNG phải identity, dù
bên trong có dòng "Giấy tờ tùy thân: Thẻ CCCD số ..." của người yêu cầu — đó chỉ là THÔNG TIN KHAI,
không phải ảnh thẻ. Tài liệu là tờ khai/đơn → type "other" và documentName ĐÚNG chuỗi "Tờ khai bản giấy"
(KHÔNG lấy tên file dài, KHÔNG thêm tên người).
divorce_or_death_proof = bản án/quyết định ly hôn hoặc giấy chứng tử của vợ/chồng.
foreign_divorce_note = trích lục ghi chú ly hôn/hủy kết hôn ở nước ngoài.
previous_marital_status_certificate_or_authorization = giấy xác nhận tình trạng hôn nhân đã cấp
trước đó hoặc văn bản ủy quyền.
title là tên tài liệu tiếng Việt ngắn để hiển thị; nếu type identity thì title là 'Căn cước công dân'.
documentName là tên ngắn gọn, CỤ THỂ theo NỘI DUNG file (dùng làm tên thành phần hồ sơ):
TUYỆT ĐỐI không đặt chung chung 'Tài liệu khác'/'Tài liệu'; nêu đúng loại giấy tờ đọc được.
Nhiều tài liệu cùng loại thì documentName phải KHÁC nhau (thêm tên người/số/đặc điểm).
Chỉ dùng chữ, số, khoảng trắng, gạch dưới, gạch ngang; tối đa ~50 ký tự.
Nếu OCR quá thiếu để biết loại giấy tờ thì để documentName rỗng.
""".strip()


def _truncate_text(text: str, limit: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    docs = [
        {
            "index": item["index"],
            "fileName": item["fileName"],
            "text": _truncate_text(item.get("text", "")),
        }
        for item in documents
    ]
    return (
        "DANH SÁCH OCR:\n"
        f"{json.dumps(docs, ensure_ascii=False)}\n\n"
        'Schema bắt buộc: {"documents":[{"index":0,"type":"identity","title":"Căn cước công dân","documentName":"Căn cước công dân"}]}'
    )
