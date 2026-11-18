"""Prompt phân loại tệp đính kèm Cấp hộ chiếu phổ thông ở trong nước (1.001456) — chế độ KHÔNG tách."""

import json

# Danh mục loại giấy dùng chung với chế độ tách (dinh_kem_tach/prompt.py).
DOC_TYPES = """
   - ho_chieu: HỘ CHIẾU phổ thông (trang nhân thân có ảnh, dòng MRZ "P<VNM…", "Số hộ chiếu / Passport No"; hoặc trang
     "CƠ QUAN CẤP HỘ CHIẾU / ISSUING AUTHORITY" có chữ ký, dấu).
   - to_khai: TỜ KHAI đề nghị cấp hộ chiếu phổ thông (tiêu đề "TỜ KHAI", "Dùng cho công dân Việt Nam đề nghị cấp hộ
     chiếu phổ thông…", các mục 1–14), kể cả khi tờ khai nhắc tới hộ chiếu cũ ở mục 13.
   - trinh_bao_mat: ĐƠN TRÌNH BÁO MẤT HỘ CHIẾU hoặc THÔNG BÁO về việc đã tiếp nhận đơn trình báo mất hộ chiếu.
   - dai_dien_hop_phap: giấy tờ chứng minh NGƯỜI ĐẠI DIỆN HỢP PHÁP của người chưa đủ 14 tuổi / mất năng lực hành vi
     dân sự (giấy khai sinh, trích lục khai sinh, quyết định cử người giám hộ, giấy tờ đăng ký giám hộ).
   - identity: thẻ căn cước / CCCD / CMND.
   - other: giấy khác."""

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại từng tệp đính kèm của hồ sơ đề nghị cấp hộ chiếu phổ thông ở trong nước.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi tệp chọn đúng MỘT docType:{DOC_TYPES}
3. documentName: CHỈ cho other — tên giấy theo TIÊU ĐỀ in trên giấy, tối đa 250 ký tự. Loại khác → "".
4. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"documents":[{{"index":0,"docType":"ho_chieu","documentName":""}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict]) -> str:
    payload = [{"index": d["index"], "OCR_TEXT": str(d.get("text") or "")[:4000]} for d in documents]
    return "Phân loại các tệp sau:\n" + json.dumps(payload, ensure_ascii=False)
