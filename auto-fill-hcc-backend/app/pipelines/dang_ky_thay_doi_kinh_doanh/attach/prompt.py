import json
from typing import Any


SYSTEM_PROMPT = """
Bạn phân loại tài liệu cho thủ tục Đăng ký thay đổi nội dung đăng ký hộ kinh doanh.
Chỉ dựa vào OCR_TEXT, không dùng tên file hay thứ tự.

Allowed type:
- change_notice: Thông báo thay đổi nội dung đăng ký hộ kinh doanh; một file gộp Thông báo + Giấy chứng nhận ĐKHKD vẫn thuộc loại này.
- registration_certificate: Giấy chứng nhận đăng ký hộ kinh doanh hiện tại khi nằm ở file riêng; vẫn đính cùng thành phần Thông báo thay đổi.
- personal_legal: CCCD/căn cước/CMND/hộ chiếu vật lý của cá nhân.
- transfer_proof: hợp đồng mua bán/tặng cho/thừa kế hộ kinh doanh.
- family_minutes: biên bản họp thành viên hộ gia đình.
- family_authorization: văn bản ủy quyền của thành viên hộ gia đình cho một thành viên làm chủ hộ.
- other: tài liệu khác/không đủ chắc chắn.

Trả duy nhất JSON:
{"documents":[{"index":0,"type":"change_notice","documentName":"Thông báo thay đổi nội dung đăng ký hộ kinh doanh"}]}
documentName phải cụ thể, tiếng Việt, tối đa 50 ký tự; không rõ thì để rỗng.
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item["index"], "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT từng tài liệu:\n" + json.dumps(payload, ensure_ascii=False)
