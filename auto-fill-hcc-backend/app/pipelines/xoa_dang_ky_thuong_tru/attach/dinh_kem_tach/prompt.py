"""Prompt chia giấy tờ theo trang khi TÁCH đính kèm Xóa đăng ký thường trú (Cổng DVC Bộ Công an)."""

import json
from typing import Any

from ..dinh_kem_khong_tach.prompt import DOC_TYPE_RULES

SYSTEM_PROMPT = f"""
<persona>
Bạn đọc các tài liệu đính kèm của hồ sơ xóa đăng ký thường trú theo TỪNG TRANG và chia chúng thành từng giấy tờ.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi giấy tờ = một nhóm trang LIÊN TIẾP của cùng một tệp. Trang tiếp theo, trang ký, phụ lục của cùng văn bản (vd
   trang 2 của hợp đồng chuyển nhượng, trang ký của biên bản) thuộc giấy liền trước. Hai mặt của CÙNG một thẻ căn
   cước / CCCD / CMND là MỘT giấy: hai mặt nằm liền nhau trong cùng tệp → một phần tử gồm cả hai trang, matThe =
   "ca_hai". Thẻ của HAI người là HAI giấy. Trang trắng hoặc chỉ có ký tự rác → docType "blank_page". Trang mở đầu
   bằng TIÊU ĐỀ của một giấy khác (vd "TỜ KHAI", "BIÊN BẢN", "HỢP ĐỒNG", "XÁC NHẬN", "GIẤY KHAI SINH") LUÔN bắt đầu
   giấy MỚI.
3. MỌI trang của MỌI tệp nằm trong đúng MỘT phần tử, kể cả trang trắng. "pages" đánh số theo trang trong tệp (từ 1).
4. docType:
{DOC_TYPE_RULES}
   - blank_page: trang trắng / ký tự rác.
5. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Tờ khai thay đổi thông tin cư trú", "Hợp đồng chuyển
   nhượng quyền sử dụng đất"). Tối đa 50 ký tự, không ngoặc, không dấu chấm, không đuôi tệp. KHÔNG dùng tên file.
   Không xác định → "". Riêng thẻ căn cước / CCCD / CMND: BẮT BUỘC trả "matThe" = "truoc" (mặt có ảnh, họ tên),
   "sau" (mặt có nơi cư trú, ngày cấp, MRZ) hoặc "ca_hai" (một trang có cả hai mặt) và "chuThe" = họ tên chủ thẻ (mặt
   sau lấy dòng MRZ cuối, vd "NGUYEN<<VAN<A" → "NGUYEN VAN A"); không đọc được → "". Giấy khác: "matThe" = "".
6. Làm HAI bước trong CÙNG một JSON:
   a. "tep": MỖI tệp có từ 2 trang trở lên một mục {{"fileIndex","tieuDeTrang"}} (tệp 1 trang KHÔNG liệt kê) —
      tieuDeTrang có ĐÚNG một mục cho MỖI trang của tệp, theo thứ tự trang. Trang ĐẦU của một giấy tờ → tên loại
      giấy đó như documentName; trang KHÔNG phải trang đầu của giấy (trang 2, 3… của cùng văn bản, mặt sau thẻ,
      trang ký, trang trắng) → "".
   b. "documents": chia giấy THEO bước a — trang có tiêu đề khác rỗng LUÔN bắt đầu giấy MỚI; trang tiêu đề rỗng
      thuộc giấy liền trước CỦA CÙNG TỆP; trang đầu mỗi tệp luôn bắt đầu phần tử mới.
7. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"tep":[{{"fileIndex":0,"tieuDeTrang":["Tờ khai thay đổi thông tin cư trú","Hợp đồng chuyển nhượng quyền sử dụng đất"]}}],"documents":[{{"fileIndex":0,"pages":[1],"docType":"to_khai","documentName":"Tờ khai thay đổi thông tin cư trú","matThe":"","chuThe":""}}]}}
</output_contract>
""".strip()


def build_user_prompt(files: list[dict[str, Any]]) -> str:
    total = sum(len(f.get("pages") or []) for f in files)
    multi = [f.get("fileIndex") for f in files if len(f.get("pages") or []) > 1]
    return ("OCR_TEXT:\n" + json.dumps(files, ensure_ascii=False)
            + f"\n\nHồ sơ có {len(files)} tệp, tổng {total} trang. \"tep\" gồm đúng {len(multi)} tệp nhiều trang "
            f"(fileIndex {multi}); \"documents\" phủ đủ {total} trang. Chia giấy tờ.")
