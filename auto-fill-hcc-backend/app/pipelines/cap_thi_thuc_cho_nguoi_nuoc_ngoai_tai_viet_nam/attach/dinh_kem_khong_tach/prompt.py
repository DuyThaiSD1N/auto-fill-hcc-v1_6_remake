"""Prompt phân loại tệp đính kèm Cấp thị thực cho người nước ngoài tại Việt Nam (1.001194) — chế độ KHÔNG tách."""

import json

# Danh mục loại giấy dùng chung với chế độ tách (dinh_kem_tach/prompt.py; ho_so_gop chỉ có ở chế độ này).
DOC_TYPES = """
   - to_khai: TỜ KHAI ĐỀ NGHỊ CẤP THỊ THỰC, GIA HẠN TẠM TRÚ (Mẫu NA5, song ngữ "APPLICATION FORM FOR VISA ISSUANCE,
     STAY EXTENSION", mục I Người đề nghị – IV Những điều cần trình bày thêm).
   - ho_chieu: HỘ CHIẾU / PASSPORT của người nước ngoài (trang nhân thân có dòng MRZ "P<…", Passport No., Surname,
     Given names; trang dấu kiểm chứng nhập cảnh "NHẬP CẢNH / ARRIVAL"; trang thị thực cũ).
   - chung_minh: giấy tờ chứng minh LÝ DO được cấp thị thực / quan hệ với người bảo lãnh: giấy chứng nhận kết hôn,
     giấy khai sinh, trích lục hộ tịch, giấy phép lao động, giấy chứng nhận đầu tư, giấy xác nhận học tập, công văn
     mời của cơ quan, tổ chức.
   - identity: thẻ căn cước / CCCD / CMND hoặc thẻ thường trú / thẻ tạm trú của NGƯỜI BẢO LÃNH.
   - bia_ho_so: trang bìa "HỒ SƠ THỦ TỤC HÀNH CHÍNH", phiếu thông tin hồ sơ, danh mục thành phần hồ sơ.
   - other: giấy khác."""

GOP_TYPE = """
   - ho_so_gop: MỘT tệp chứa cả TỜ KHAI NA5 lẫn giấy tờ chứng minh lý do (vd bìa + tờ khai + hộ chiếu + giấy chứng nhận
     kết hôn + căn cước trong cùng một PDF)."""

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại từng tệp đính kèm của hồ sơ đề nghị cấp thị thực cho người nước ngoài đang tạm trú tại Việt Nam.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi tệp chọn đúng MỘT docType:{DOC_TYPES}{GOP_TYPE}
3. documentName: CHỈ cho other — tên giấy theo TIÊU ĐỀ in trên giấy, tối đa 250 ký tự. Loại khác → "".
4. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"documents":[{{"index":0,"docType":"to_khai","documentName":""}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict]) -> str:
    payload = [{"index": d["index"], "OCR_TEXT": str(d.get("text") or "")[:4000]} for d in documents]
    return "Phân loại các tệp sau:\n" + json.dumps(payload, ensure_ascii=False)
