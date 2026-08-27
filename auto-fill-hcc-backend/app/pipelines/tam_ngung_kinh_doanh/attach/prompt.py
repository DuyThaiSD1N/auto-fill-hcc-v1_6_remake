import json
from typing import Any


SYSTEM_PROMPT = """
Bạn phân loại tài liệu cho thủ tục Tạm ngừng kinh doanh hộ kinh doanh.
Chỉ dựa vào OCR_TEXT, không dùng tên file hoặc thứ tự.

Allowed type:
- suspension_notice: Giấy đề nghị đăng ký tạm ngừng kinh doanh (thành phần hồ sơ chính, ghi rõ thời
  gian tạm ngừng "kể từ ngày ... đến hết ngày ..." và lý do tạm ngừng).
- registration_certificate: Bản gốc/bản scan Giấy chứng nhận đăng ký hộ kinh doanh.
- other: CCCD, ủy quyền và mọi tài liệu khác/không đủ chắc chắn.

Nếu một file scan gộp có Thông báo tạm ngừng ở trang đầu và kèm GCN ở các trang sau,
phân loại file đó là suspension_notice vì đây là thành phần chính của bộ hồ sơ.

Trả duy nhất JSON:
{"documents":[{"index":0,"type":"suspension_notice","documentName":"Thông báo tạm ngừng kinh doanh HKD"}]}
documentName phải cụ thể, tiếng Việt, tối đa 50 ký tự; không rõ thì để rỗng.
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item["index"], "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT từng tài liệu:\n" + json.dumps(payload, ensure_ascii=False)
