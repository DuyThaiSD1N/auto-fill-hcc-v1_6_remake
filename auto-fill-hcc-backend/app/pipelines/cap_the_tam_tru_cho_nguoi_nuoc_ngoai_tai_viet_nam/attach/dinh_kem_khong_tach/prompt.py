"""Prompt phân loại tệp đính kèm Cấp thẻ tạm trú cho người nước ngoài (1.003460) — chế độ KHÔNG tách."""

import json

# Danh mục loại giấy dùng chung với chế độ tách (dinh_kem_tach/prompt.py; ho_so_gop chỉ có ở chế độ này).
DOC_TYPES = """
   - to_khai: TỜ KHAI ĐỀ NGHỊ CẤP THẺ TẠM TRÚ (Mẫu NA8, song ngữ "INFORMATION FORM FOR A TEMPORARY RESIDENT CARD",
     mục 1–12, có ô dán ảnh).
   - van_ban: VĂN BẢN ĐỀ NGHỊ CẤP THẺ TẠM TRÚ của cơ quan, tổ chức (Mẫu NA6, công văn "V/v đề nghị cấp thẻ tạm trú") hoặc
     của cá nhân bảo lãnh (Mẫu NA7).
   - ho_chieu: HỘ CHIẾU / PASSPORT của người nước ngoài (trang nhân thân có dòng MRZ "P<…"; trang THỊ THỰC VIỆT NAM;
     trang dấu kiểm chứng nhập cảnh "NHẬP CẢNH / ARRIVAL").
   - chung_minh: giấy tờ chứng minh thuộc diện xem xét cấp thẻ tạm trú: GIẤY PHÉP LAO ĐỘNG / WORK PERMIT, giấy xác nhận
     không thuộc diện cấp giấy phép lao động, giấy chứng nhận đầu tư, giấy xác nhận Trưởng văn phòng đại diện, giấy chứng
     nhận kết hôn / khai sinh (bảo lãnh thân nhân).
   - identity: thẻ căn cước / CCCD / CMND của công dân Việt Nam (người bảo lãnh / người nộp).
   - bia_ho_so: trang bìa "HỒ SƠ THỦ TỤC HÀNH CHÍNH", phiếu thông tin hồ sơ, danh mục thành phần hồ sơ.
   - other: giấy khác."""

GOP_TYPE = """
   - ho_so_gop: MỘT tệp chứa từ HAI loại giấy trở lên ở trên (vd bìa + văn bản NA6 + tờ khai NA8 + hộ chiếu + giấy phép
     lao động trong cùng một PDF)."""

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại từng tệp đính kèm của hồ sơ đề nghị cấp thẻ tạm trú cho người nước ngoài tại Việt Nam.
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
