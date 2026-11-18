"""Prompt phân loại tệp đính kèm Đăng ký mẫu con dấu mới (2.001428) — chế độ KHÔNG tách (mỗi tệp một loại)."""

import json

# Danh mục loại giấy dùng chung với chế độ tách (dinh_kem_tach/prompt.py).
DOC_TYPES = """
   - quyet_dinh_thanh_lap: QUYẾT ĐỊNH thành lập / công nhận / cho phép hoạt động / giấy phép thành lập của chính cơ quan,
     tổ chức đề nghị đăng ký con dấu (kể cả danh sách, phụ lục kèm theo quyết định).
   - van_ban_de_nghi: văn bản đề nghị đăng ký mẫu con dấu (Mẫu số 03, "V/v đề nghị đăng ký mẫu con dấu", có các mục
     "Cơ quan, tổ chức đề nghị đăng ký mẫu con dấu", "Người được giới thiệu/uỷ quyền liên hệ nộp hồ sơ").
   - giay_gioi_thieu: GIẤY GIỚI THIỆU hoặc GIẤY ỦY QUYỀN riêng cho người đi nộp hồ sơ (văn bản có tiêu đề "GIẤY GIỚI
     THIỆU" / "GIẤY ỦY QUYỀN"), KHÔNG phải văn bản đề nghị.
   - van_ban_dong_y: văn bản của cơ quan có thẩm quyền ĐỒNG Ý / cho phép khắc dấu, khắc mới con dấu (vd công văn của Ban
     Tổ chức cấp ủy cấp trên "V/v khắc mới con dấu …"), KHÔNG phải văn bản đề nghị của chính tổ chức.
   - identity: thẻ căn cước / CCCD / CMND / hộ chiếu.
   - other: giấy khác."""

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại từng tệp đính kèm của hồ sơ đăng ký mẫu con dấu mới của cơ quan, tổ chức.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi tệp chọn đúng MỘT docType:{DOC_TYPES}
3. Văn bản đề nghị cũng có dòng "V/v đề nghị đăng ký mẫu con dấu" và nhắc tới quyết định thành lập, công văn đồng ý
   trong mục "Các tài liệu trong hồ sơ gửi kèm theo" → vẫn là van_ban_de_nghi.
4. documentName: CHỈ cho van_ban_dong_y và other — tên văn bản theo dạng "<Loại văn bản> số <số>, ngày <d/m/yyyy> của
   <cơ quan ban hành> V/v <trích yếu>" (vd "Công văn số 12-CV/BTCTU, ngày 5/9/2026 của Ban Tổ chức Tỉnh ủy An Bình V/v
   khắc mới con dấu cho các đảng ủy trực thuộc"), chép số và trích yếu đúng chữ trên giấy, tối đa 250 ký tự. Loại khác
   → "".
5. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"documents":[{{"index":0,"docType":"van_ban_de_nghi","documentName":""}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict]) -> str:
    payload = [{"index": d["index"], "OCR_TEXT": str(d.get("text") or "")[:4000]} for d in documents]
    return "Phân loại các tệp sau:\n" + json.dumps(payload, ensure_ascii=False)
