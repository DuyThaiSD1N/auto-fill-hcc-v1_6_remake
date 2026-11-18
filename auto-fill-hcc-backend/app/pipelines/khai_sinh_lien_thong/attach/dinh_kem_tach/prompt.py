"""Prompt chia giấy tờ theo trang khi TÁCH đính kèm đăng ký khai sinh liên thông."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn đọc các tài liệu đính kèm của hồ sơ đăng ký khai sinh liên thông theo TỪNG TRANG và chia chúng thành từng giấy
tờ. Cán bộ hay scan cả bộ hồ sơ thành MỘT tệp nhiều trang (giấy chứng sinh, giấy kết hôn, căn cước cha mẹ, tờ khai
cư trú...), nên mỗi trang phải được xếp đúng vào giấy của nó.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi giấy tờ = một nhóm trang LIÊN TIẾP của cùng một tệp. Trang tiếp theo của cùng văn bản, mặt sau in sẵn, trang
   chỉ còn ngày tháng / chữ ký / con dấu thuộc giấy liền trước. Hai mặt của CÙNG một thẻ CCCD / thẻ căn cước / CMND
   nằm liền nhau là MỘT giấy (một phần tử gồm cả hai trang). Thẻ của hai người khác nhau là hai giấy.
   Trang mở đầu bằng TIÊU ĐỀ của một giấy khác (vd "GIẤY CHỨNG SINH", "GIẤY CHỨNG NHẬN KẾT HÔN", "TỜ KHAI...",
   "CĂN CƯỚC", "GIẤY CAM ĐOAN") LUÔN bắt đầu giấy MỚI.
3. MỌI trang của MỌI tệp nằm trong đúng MỘT phần tử, kể cả trang trắng. "pages" đánh số theo trang trong tệp (từ 1).
4. docType:
   - birth_proof: GIẤY CHỨNG SINH, văn bản người làm chứng xác nhận việc sinh, hoặc giấy cam đoan về việc sinh.
     OCR có thể mất tiêu đề "GIẤY CHỨNG SINH"; vẫn nhận ra mẫu qua "Mã số GCS", "Đã sinh con vào lúc … giờ … ngày …",
     "Số con trong lần sinh này", "Cân nặng", "Người đỡ đẻ", chữ ký đại diện cơ sở khám bệnh, chữa bệnh.
   - residence_form: TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ (mẫu CT01), kể cả trang ý kiến / chữ ký các thành phần.
   - birth_declaration: TỜ KHAI ĐĂNG KÝ KHAI SINH. Tờ khai có câu "Tôi cam đoan ... khai sinh" vẫn là
     birth_declaration, KHÔNG phải birth_proof.
   - other: mọi giấy khác — CCCD / CMND / thẻ căn cước / hộ chiếu của cha mẹ, giấy chứng nhận kết hôn, sổ hộ khẩu,
     giấy ủy quyền...
   - blank_page: trang trắng hoặc chỉ có ký tự rác.
   Không đủ bằng chứng cho birth_proof / residence_form / birth_declaration → other.
5. documentName: tên giấy theo TIÊU ĐỀ in trên giấy (vd "Giấy chứng sinh", "Giấy chứng nhận kết hôn", "Căn cước công
   dân", "Tờ khai thay đổi thông tin cư trú"); giấy không có tiêu đề thì gọi đúng loại giấy. Tối đa 50 ký tự, chỉ
   chữ, số và dấu cách — không ngoặc, không dấu chấm, không gạch dưới, không đuôi tệp, không tên người.
   KHÔNG dùng tên file, KHÔNG ghi chung chung "Tài liệu khác". Không xác định được → "".
6. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{"documents":[{"fileIndex":0,"pages":[1],"docType":"birth_proof","documentName":"Giấy chứng sinh"},{"fileIndex":0,"pages":[2,3],"docType":"other","documentName":"Căn cước công dân"}]}
</output_contract>
""".strip()


def build_user_prompt(files: list[dict[str, Any]]) -> str:
    total = sum(len(f.get("pages") or []) for f in files)
    # Mốc số lượng: hồ sơ nhiều tệp / nhiều trang, model hay dừng sau giấy đầu.
    return ("OCR_TEXT:\n" + json.dumps(files, ensure_ascii=False)
            + f"\n\nHồ sơ có {len(files)} tệp, tổng {total} trang; \"documents\" phủ đủ {total} trang. Chia giấy tờ.")
