import json
from typing import Any


SYSTEM_PROMPT = """
Bạn phân loại tài liệu cho thủ tục cấp lại/cấp đổi Giấy chứng nhận đăng ký hộ kinh doanh.
Chỉ dựa vào OCR_TEXT, không dùng tên file hoặc thứ tự.

Allowed type:
- reissue_application: Giấy đề nghị cấp lại/cấp đổi Giấy chứng nhận đăng ký hộ kinh doanh (Mẫu số 2).
- other: CCCD, GCN cũ, ủy quyền và mọi tài liệu khác/không đủ chắc chắn.

Nếu một file scan gộp có Mẫu số 2 ở trang đầu và kèm CCCD/GCN ở trang sau, phân loại file đó là
reissue_application vì đây là thành phần chính của bộ hồ sơ.

Trả duy nhất JSON:
{"documents":[{"index":0,"type":"reissue_application","documentName":"Giấy đề nghị cấp lại GCN hộ kinh doanh"}]}
documentName phải cụ thể, tiếng Việt, tối đa 50 ký tự; không rõ thì để rỗng.
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item["index"], "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT từng tài liệu:\n" + json.dumps(payload, ensure_ascii=False)
