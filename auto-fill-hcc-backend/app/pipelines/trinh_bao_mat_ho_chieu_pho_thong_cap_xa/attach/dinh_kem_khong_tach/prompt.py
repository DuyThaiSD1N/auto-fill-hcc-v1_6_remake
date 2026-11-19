"""Prompt phân loại tệp đính kèm Trình báo mất hộ chiếu phổ thông cấp xã (1.010386) — chế độ KHÔNG tách."""

import json

# Danh mục loại giấy dùng chung với chế độ tách (dinh_kem_tach/prompt.py).
DOC_TYPES = """
   - trinh_bao_mat: ĐƠN TRÌNH BÁO MẤT HỘ CHIẾU PHỔ THÔNG (Mẫu TK05: "Kính gửi", mục 1–9, "Hoàn cảnh và lý do cụ thể
     bị mất hộ chiếu", "Người trình báo").
   - to_khai: TỜ KHAI đề nghị cấp hộ chiếu phổ thông (tiêu đề "TỜ KHAI", "Dùng cho công dân Việt Nam đề nghị cấp hộ
     chiếu phổ thông…", ảnh 4x6, mục 1–14), kể cả khi mục 14 ghi "cấp lại hộ chiếu do bị mất".
   - identity: thẻ căn cước / CCCD / CMND.
   - other: giấy khác."""

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại từng tệp đính kèm của hồ sơ trình báo mất hộ chiếu phổ thông.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi tệp chọn đúng MỘT docType:{DOC_TYPES}
3. documentName: CHỈ cho other — tên giấy theo TIÊU ĐỀ in trên giấy, tối đa 250 ký tự. Loại khác → "".
4. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"documents":[{{"index":0,"docType":"trinh_bao_mat","documentName":""}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict]) -> str:
    payload = [{"index": d["index"], "OCR_TEXT": str(d.get("text") or "")[:4000]} for d in documents]
    return "Phân loại các tệp sau:\n" + json.dumps(payload, ensure_ascii=False)
