import json
from typing import Any


SYSTEM_PROMPT = """
Bạn phân loại tài liệu cho thủ tục Chấm dứt hoạt động hộ kinh doanh.
Chỉ dựa vào OCR_TEXT, không dùng tên file hoặc thứ tự.

Allowed type:
- dissolution_notice: Thông báo về việc chấm dứt hoạt động hộ kinh doanh (Mẫu số 1).
- tax_termination_notice: Thông báo của cơ quan thuế về chấm dứt hiệu lực mã số thuế hoặc hoàn thành nghĩa vụ nộp thuế để giải thể.
- registration_certificate: Bản gốc/bản scan Giấy chứng nhận đăng ký hộ kinh doanh.
- family_minutes: Biên bản họp thành viên hộ gia đình về việc chấm dứt hoạt động HKD.
- other: CCCD, ủy quyền và mọi tài liệu khác/không đủ chắc chắn.

Phân loại theo TIÊU ĐỀ và bản chất văn bản. Văn bản ỦY QUYỀN (có "Bên ủy quyền"/"Bên được ủy quyền")
luôn là other, kể cả khi nội dung nhắc "thông báo về việc chấm dứt hoạt động hộ kinh doanh" hay số Giấy
chứng nhận đăng ký hộ kinh doanh — đó chỉ là phạm vi ủy quyền.

Nếu một file scan gộp có Mẫu số 1 ở trang đầu và kèm GCN/Thông báo thuế ở các trang sau,
phân loại file đó là dissolution_notice vì đây là thành phần chính của bộ hồ sơ.

Trả duy nhất JSON:
{"documents":[{"index":0,"type":"dissolution_notice","documentName":"Thông báo chấm dứt hoạt động HKD"}]}
documentName phải cụ thể, tiếng Việt, tối đa 50 ký tự; không rõ thì để rỗng.
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item["index"], "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT từng tài liệu:\n" + json.dumps(payload, ensure_ascii=False)
