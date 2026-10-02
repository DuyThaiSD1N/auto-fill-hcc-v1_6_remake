"""Prompt nhận diện Văn bản đề nghị + đặt tên tài liệu cho đính kèm [Lào Cai] chủ trương đầu tư."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn đọc tài liệu đính kèm của hồ sơ đề nghị chấp thuận / điều chỉnh chủ trương đầu tư trên cổng dịch vụ công
tỉnh Lào Cai: xác định tài liệu có phải VĂN BẢN ĐỀ NGHỊ hay không và đặt tên ngắn cho tài liệu.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file hay giả định bên ngoài.
2. docType:
   - van_ban_de_nghi: "VĂN BẢN ĐỀ NGHỊ THỰC HIỆN DỰ ÁN ĐẦU TƯ" hoặc "VĂN BẢN ĐỀ NGHỊ ĐIỀU CHỈNH DỰ ÁN ĐẦU TƯ" do
     nhà đầu tư lập ("Kính gửi: Ban Quản lý…", mục "I. Nhà đầu tư", người đại diện theo pháp luật ký).
   - other: mọi tài liệu khác (đề xuất / thuyết minh dự án, báo cáo, quyết định, biên bản, báo cáo tài chính,
     giấy chứng nhận, hợp đồng, bản vẽ…). Tờ trình / quyết định có TRÍCH DẪN văn bản đề nghị vẫn là other.
3. documentName: TÊN TIẾNG VIỆT CÓ DẤU, ngắn gọn theo nội dung (≤ 60 ký tự), kèm số hiệu/năm/lần để phân biệt
   các tài liệu cùng loại — vd "Báo cáo tài chính năm 2024", "GCN đăng ký doanh nghiệp thay đổi lần 7",
   "QĐ 130-QĐ-UBND cho thuê đất". KHÔNG chép tên tệp, không ngoặc kép. OCR quá thiếu thì để trống.
4. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{"documents":[{"index":0,"docType":"other","documentName":"Báo cáo tài chính năm 2024"}]}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False) + "\n\nPhân loại và đặt tên tài liệu."
