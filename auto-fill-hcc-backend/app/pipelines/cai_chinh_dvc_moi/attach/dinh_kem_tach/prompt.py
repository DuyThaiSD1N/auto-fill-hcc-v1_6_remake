"""Prompt chia giấy tờ theo trang khi TÁCH đính kèm thay đổi, cải chính, bổ sung thông tin hộ tịch."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn đọc các tài liệu đính kèm của hồ sơ thay đổi, cải chính, bổ sung thông tin hộ tịch theo TỪNG TRANG và chia
chúng thành từng giấy tờ.
</persona>

<critical_rules>
1. Chỉ dùng OCR_TEXT; KHÔNG dùng tên file.
2. Mỗi giấy tờ = một nhóm trang LIÊN TIẾP của cùng một tệp. Trang chú thích / mặt sau in sẵn của tờ khai, giấy khai
   sinh, trích lục và trang tiếp theo của cùng văn bản thuộc giấy liền trước. Hai mặt của CÙNG một thẻ CCCD / thẻ
   căn cước / CMND là MỘT giấy, KHÔNG tách: hai mặt nằm liền nhau trong cùng tệp → một phần tử gồm cả hai trang,
   matThe = "ca_hai". Trang trắng hoặc chỉ có ký tự
   rác → docType "blank_page".
   Trang mở đầu bằng TIÊU ĐỀ của một giấy khác (vd "BẢN CAM ĐOAN", "TỜ KHAI", "GIẤY ỦY QUYỀN", "GIẤY CHỨNG NHẬN")
   LUÔN bắt đầu giấy MỚI, kể cả khi nằm ngay sau trang ghi chú / mặt sau của giấy trước. Trang chỉ còn dòng ngày
   tháng, chữ ký, con dấu của giấy liền trước thuộc giấy đó, KHÔNG phải blank_page.
3. MỌI trang của MỌI tệp nằm trong đúng MỘT phần tử, kể cả trang trắng. "pages" đánh số theo trang trong tệp (từ 1).
4. docType:
   - uy_quyen: giấy ủy quyền / hợp đồng ủy quyền / văn bản ủy quyền thực hiện việc đăng ký hộ tịch (có bên ủy
     quyền và bên được ủy quyền), kể cả khi kèm trang chứng thực chữ ký.
   - other: mọi tài liệu khác — tờ khai, CCCD/CMND, giấy khai sinh, trích lục, giấy tờ làm căn cứ (học bạ,
     bằng cấp, giấy xác nhận, quyết định...). Tờ khai có dòng "người được ủy quyền" vẫn là other.
   - blank_page: trang trắng / ký tự rác.
5. documentName: tên giấy tờ theo TIÊU ĐỀ in trên giấy (vd "Căn cước công dân", "Giấy khai sinh",
   "Tờ khai thay đổi cải chính hộ tịch"); giấy không có tiêu đề thì gọi đúng loại giấy. Tối đa 50 ký tự, không
   ngoặc, không dấu chấm, không đuôi tệp. KHÔNG dùng tên file, KHÔNG ghi chung chung "Tài liệu khác". Không xác
   định được → "".
   Riêng thẻ CCCD / thẻ căn cước / CMND (kể cả CMND cũ 9 số): BẮT BUỘC trả "matThe" khác rỗng = "truoc" (mặt có
   ảnh, họ tên), "sau" (mặt có đặc điểm nhận dạng, vân tay, 3 dòng MRZ) hoặc "ca_hai" (MỘT trang/ảnh chụp cả hai
   mặt: vừa có họ tên vừa có vân tay / MRZ) và "chuThe" = họ tên chủ thẻ — có dòng "Họ và tên" thì chép nguyên dấu,
   mặt sau lấy dòng MRZ cuối (vd "NGUYEN<<VAN<A" → "NGUYEN VAN A") — KHÔNG lấy tên người ký in trên mặt sau
   (tên dưới "CỤC TRƯỞNG CỤC CẢNH SÁT…" / "DIRECTOR GENERAL…"); không đọc được → "". Giấy khác: "matThe" = "".
6. Làm HAI bước trong CÙNG một JSON:
   a. "tep": MỖI tệp có từ 2 trang trở lên một mục {"fileIndex","tieuDeTrang"} (tệp 1 trang KHÔNG liệt kê) —
      tieuDeTrang có ĐÚNG một mục cho MỖI trang của tệp, theo thứ tự trang. Trang là trang ĐẦU của một giấy tờ → tên loại giấy đó như documentName (vd "Căn cước công
      dân", "Giấy khai sinh", "Bản cam đoan", "Tờ khai...", "Quyết định..."). Trang KHÔNG phải trang đầu của giấy →
      "": trang 2, 3... của cùng văn bản (kể cả khi lặp lại tiêu đề), mặt sau thẻ, trang ghi chú / phụ lục / lời
      chứng in kèm giấy ("PHẦN GHI CHÚ...", "LỜI CHỨNG CHỨNG THỰC" là MỤC của giấy, không phải giấy), trang ký, trang
      rác / trắng.
   b. "documents": chia giấy THEO bước a — trang có tiêu đề khác rỗng LUÔN bắt đầu giấy MỚI; trang tiêu đề rỗng
      thuộc giấy liền trước CỦA CÙNG TỆP (mặt sau thẻ CCCD gộp với mặt trước của cùng thẻ); trang đầu mỗi tệp luôn
      bắt đầu phần tử mới (tệp chỉ có mặt sau thẻ → phần tử riêng, matThe "sau").
7. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{"tep":[{"fileIndex":0,"tieuDeTrang":["Giấy khai sinh",""]}],"documents":[{"fileIndex":0,"pages":[1,2],"docType":"other","documentName":"Giấy khai sinh","matThe":"","chuThe":""}]}
</output_contract>
""".strip()


def build_user_prompt(files: list[dict[str, Any]]) -> str:
    total = sum(len(f.get("pages") or []) for f in files)
    multi = [f.get("fileIndex") for f in files if len(f.get("pages") or []) > 1]
    # Mốc số lượng: hồ sơ nhiều tệp, model hay dừng sau tệp đầu (hoặc lặp "tep" vô tận khi nhiều ảnh 1 trang).
    return ("OCR_TEXT:\n" + json.dumps(files, ensure_ascii=False)
            + f"\n\nHồ sơ có {len(files)} tệp, tổng {total} trang. \"tep\" gồm đúng {len(multi)} tệp nhiều trang "
            f"(fileIndex {multi}); \"documents\" phủ đủ {total} trang. Chia giấy tờ.")

CONFIRM_PROMPT = """
Bạn kiểm tra ranh giới giấy tờ trong hồ sơ scan. Mỗi mục có "giayTruoc" (chữ OCR trang ĐẦU của một giấy) và
"trangSau" (một trang nằm sau nó trong cùng tệp). Chỉ dùng chữ OCR.
- "trangSau" là trang ĐẦU của một giấy tờ KHÁC, độc lập với giấy trước (vd bản cam đoan, tờ khai, đơn, giấy ủy quyền,
  quyết định, giấy chứng nhận, thẻ CCCD của người khác) → "giayMoi": true.
- "trangSau" là MỘT PHẦN của giấy trước (trang tiếp theo, phần ghi chú / mặt sau in sẵn của chính giấy đó, phụ lục,
  lời chứng chứng thực, trang ký, mặt sau thẻ) → "giayMoi": false.
Trả DUY NHẤT JSON: {"answers":[{"id":0,"giayMoi":true}]}
""".strip()


def build_confirm_prompt(items: list[dict[str, Any]]) -> str:
    return "CAC_TRANG:\n" + json.dumps(items, ensure_ascii=False) + "\n\nTrả lời từng id."
