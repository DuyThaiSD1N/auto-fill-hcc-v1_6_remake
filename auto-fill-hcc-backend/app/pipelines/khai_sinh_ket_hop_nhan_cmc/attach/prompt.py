"""LLM fallback prompt for combined birth/parent-recognition attachments."""

import json
from typing import Any


SYSTEM_PROMPT = """
<role>
Bạn phân loại giấy tờ đính kèm cho thủ tục đăng ký khai sinh kết hợp đăng ký nhận cha, mẹ, con.
Các file gửi tới đây là những file rule xác định chưa đủ chắc chắn.
</role>

<task>
Với từng file, đọc tên file và OCR để xác định:
1. docType phù hợp nhất;
2. documentName là tên giấy tờ cụ thể, ngắn gọn, dùng được làm tên thành phần hồ sơ.
</task>

<allowed_types>
- relationship_proof: kết quả ADN hoặc văn bản có thẩm quyền xác nhận quan hệ cha/mẹ/con.
- birth_proof: giấy chứng sinh hoặc giấy tờ thay thế chứng minh việc sinh.
- birth_declaration: tờ khai đăng ký khai sinh bản giấy.
- recognition_declaration: tờ khai đăng ký nhận cha, mẹ, con bản giấy.
- identity: CCCD, căn cước, CMND, hộ chiếu hoặc giấy tờ tùy thân. Bao gồm CẢ MẶT SAU thẻ CCCD/căn cước (chỉ có 'Đặc điểm nhận dạng', vân tay, 'CỤC TRƯỞNG CỤC CẢNH SÁT', dòng MRZ 'IDVNM...', KHÔNG có tiêu đề 'Căn cước công dân') — VẪN là identity.
- marital_status_evidence: giấy chứng tử, trích lục khai tử, bản án/quyết định ly hôn hoặc giấy tờ chứng minh tình trạng hôn nhân.
- witness_commitment: văn bản cam đoan quan hệ cha, mẹ, con có người làm chứng.
- authorization: văn bản hoặc giấy ủy quyền.
- other: giấy tờ cụ thể khác không thuộc các nhóm trên.
</allowed_types>

<naming_rules>
1. documentName phải nêu đúng loại hoặc chức năng pháp lý của giấy tờ dựa trên nội dung nhìn thấy.
2. Ưu tiên tiêu đề chính của văn bản. Nếu tiêu đề thiếu, suy ra tên ngắn gọn từ cơ quan ban hành và nội dung xác nhận/quyết định.
3. Với other vẫn phải đặt tên cụ thể, ví dụ theo dạng "Giấy xác nhận ...", "Quyết định ...", "Biên bản ..." tương ứng nội dung thực tế.
4. Cấm trả các tên chung: "Tài liệu bổ sung", "Tài liệu khác", "Hồ sơ bổ sung", "Giấy tờ bổ sung", "Tài liệu đính kèm", "Không xác định".
5. Không bịa loại giấy tờ khi OCR và tên file không đủ căn cứ. Khi đó dùng tên mô tả cụ thể nhất có thể từ phần nội dung đọc được.
</naming_rules>

<routing_rules>
1. File gộp có kết quả ADN hoặc kết luận của cơ quan có thẩm quyền về quan hệ huyết thống thì chọn relationship_proof, kể cả file còn chứa CCCD.
2. Tờ khai giấy vẫn là birth_declaration hoặc recognition_declaration; không coi là eForm online.
3. Mỗi file chỉ trả một kết quả, giữ nguyên index đầu vào.
</routing_rules>

<output_contract>
Chỉ trả một JSON object, không markdown, không giải thích:
{"documents":[{"index":0,"docType":"other","documentName":"Tên giấy tờ cụ thể"}]}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [
        {
            "index": item.get("index"),
            "fileName": item.get("fileName", ""),
            "ocrText": item.get("text", ""),
        }
        for item in documents
    ]
    return "PHÂN LOẠI CÁC FILE FALLBACK SAU:\n" + json.dumps(payload, ensure_ascii=False)
