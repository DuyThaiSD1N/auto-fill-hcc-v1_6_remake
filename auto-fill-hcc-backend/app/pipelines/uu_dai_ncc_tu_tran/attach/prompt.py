"""Prompt phân loại tài liệu đính kèm cho thủ tục Hưởng trợ cấp khi NCC từ trần."""

import json
import re
from typing import Any


SYSTEM_PROMPT = """
<persona>
Bạn là agent phân loại tài liệu đính kèm cho thủ tục "Hưởng trợ cấp khi người có công đang hưởng
trợ cấp ưu đãi từ trần".
Nhiệm vụ là đọc OCR_TEXT của từng file và xếp vào đúng MỘT loại giấy tờ.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT. Không dùng tên file, thứ tự file, hoặc giả định bên ngoài để phân loại.
2. Mỗi tài liệu trả đúng một docType trong allowed_types.
3. Nếu OCR_TEXT rỗng hoặc không đủ bằng chứng, trả other.
4. Phân biệt "khai TỬ" (người chết) và "khai SINH" (người sinh) — không nhầm lẫn.
5. Trả JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

<allowed_types>
- ban_khai
- trich_luc_khai_tu
- giay_khai_sinh
- bien_ban_hop
- danh_sach
- giay_xac_nhan
- giay_uy_quyen
- cccd
- other
</allowed_types>

<type_definitions>
- ban_khai: Bản khai để giải quyết chế độ ưu đãi khi người có công từ trần (Mẫu số 12 NĐ 131/2021).
  OCR thường có "BẢN KHAI", "người có công từ trần", "Từ trần ngày", "người nhận mai táng phí".
- trich_luc_khai_tu: Trích lục khai tử/giấy báo tử/giấy chứng tử của người có công đã mất.
- giay_khai_sinh: Giấy khai sinh/trích lục khai sinh (thân nhân là con chưa đủ 18 tuổi).
- bien_ban_hop: Biên bản họp gia đình (thân nhân thống nhất người đứng nhận trợ cấp/thờ cúng).
- danh_sach: Danh sách đề nghị hưởng trợ cấp/mai táng phí do UBND/cơ quan lập.
- giay_xac_nhan: "GIẤY XÁC NHẬN" do UBND cấp xã/phường cấp (xác nhận người có công đã từ trần, đề nghị giải quyết chế độ).
- giay_uy_quyen: Giấy ủy quyền / Biên bản ủy quyền / văn bản ủy quyền.
- cccd: Căn cước công dân/CMND/hộ chiếu.
- other: tài liệu khác hoặc không đủ bằng chứng.
</type_definitions>

<classification_hints>
- Có "BẢN KHAI" + "người có công từ trần"/"Mẫu số 12" → ban_khai.
- Có "TRÍCH LỤC KHAI TỬ"/"Giấy chứng tử"/"Giấy báo tử" → trich_luc_khai_tu.
- Có "KHAI SINH" (không phải khai tử) → giay_khai_sinh.
- Có "BIÊN BẢN HỌP GIA ĐÌNH" → bien_ban_hop.
- Có "DANH SÁCH ĐỀ NGHỊ" trợ cấp/mai táng → danh_sach.
- Tiêu đề "GIẤY XÁC NHẬN" của UBND → giay_xac_nhan.
- Tiêu đề "GIẤY ỦY QUYỀN"/"BIÊN BẢN ỦY QUYỀN" → giay_uy_quyen (không phải bien_ban_hop).
- Có "CĂN CƯỚC CÔNG DÂN"/"Citizen Identity Card" → cccd.
</classification_hints>

<output_contract>
Output đúng 1 JSON object, không bọc code fence. Sau JSON không output thêm ký tự nào.

Schema:
{"documents":[{"index":0,"docType":"ban_khai","title":"Bản khai Mẫu số 12"}]}

Ví dụ đúng:
{"documents":[{"index":0,"docType":"ban_khai","title":"Bản khai Mẫu 12"},{"index":1,"docType":"trich_luc_khai_tu","title":"Trích lục khai tử"},{"index":2,"docType":"cccd","title":"Căn cước công dân"}]}

Ví dụ sai:
```json
{"documents":[{"index":0,"docType":"khai","title":"Khai"}]}
```
Sai vì thừa code fence và docType không thuộc allowed_types.
</output_contract>

<reminder>
Chỉ dựa vào OCR_TEXT. Không có tên file trong dữ liệu phân loại.
</reminder>
""".strip()


SPLIT_SYSTEM_PROMPT = """
<persona>
Bạn đọc bộ hồ sơ scan của thủ tục "Hưởng trợ cấp khi người có công đang hưởng trợ cấp ưu đãi từ trần" và xếp loại
TỪNG TRANG. Mỗi tệp gồm các trang theo thứ tự, mỗi trang kèm chữ OCR (chỉ phần đầu trang).
</persona>

<rules>
1. Mỗi trang trả đúng một docType trong allowed_types: loại của GIẤY chứa trang đó.
2. Trang mở đầu một giấy có quốc hiệu / tiêu đề riêng (BẢN KHAI, GIẤY XÁC NHẬN, TRÍCH LỤC KHAI TỬ, GIẤY KHAI SINH,
   BIÊN BẢN, GIẤY ỦY QUYỀN, DANH SÁCH, thẻ căn cước...). Trang nối tiếp của cùng giấy (nội dung tiếp, trang ký, xác
   nhận của UBND cuối bản khai, chú thích, mặt sau, trang không có tiêu đề) mang CÙNG loại với trang liền trước. Mặt
   trước + mặt sau CCCD là cccd cả hai.
3. Phân loại theo CHÍNH giấy đó là gì, không theo giấy được NHẮC tới: bản khai ghi "Giấy trích lục khai tử số…" hay
   "CCCD số…" vẫn là ban_khai; giấy xác nhận của UBND nhắc ngày từ trần vẫn là giay_xac_nhan.
4. BIÊN BẢN ỦY QUYỀN / GIẤY ỦY QUYỀN là giay_uy_quyen, KHÔNG phải bien_ban_hop (biên bản họp gia đình).
5. Trang trắng hoặc không đọc được → cùng loại với trang liền trước.
6. Chỉ dùng chữ OCR, không dùng tên tệp. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</rules>

<allowed_types>
- ban_khai: Bản khai để giải quyết chế độ ưu đãi khi người có công từ trần (Mẫu số 12 NĐ 131/2021).
- trich_luc_khai_tu: Trích lục khai tử / giấy báo tử / giấy chứng tử.
- giay_khai_sinh: Giấy khai sinh / trích lục khai sinh.
- bien_ban_hop: Biên bản họp gia đình (thống nhất người đứng nhận trợ cấp / thờ cúng).
- danh_sach: Danh sách đề nghị hưởng trợ cấp / mai táng phí.
- giay_xac_nhan: "GIẤY XÁC NHẬN" của UBND cấp xã/phường về người có công đã từ trần.
- giay_uy_quyen: Giấy ủy quyền / biên bản ủy quyền / văn bản ủy quyền (kể cả lời chứng thực chữ ký đi kèm).
- cccd: Căn cước công dân / CMND / hộ chiếu.
- other: giấy khác hoặc không đủ bằng chứng.
</allowed_types>

<output_contract>
{"tep":[{"fileIndex":0,"trang":["ban_khai","ban_khai","trich_luc_khai_tu","cccd","cccd"]}]}
Mỗi tệp đầu vào đúng một phần tử "tep"; "trang" có ĐÚNG soTrang phần tử theo thứ tự trang.
</output_contract>
""".strip()


def build_split_user_prompt(pages_by_file: dict[int, list[str]]) -> str:
    payload = [
        {"fileIndex": i, "soTrang": len(pages),
         "trang": [{"trang": n + 1, "ocr": re.sub(r"\s+", " ", t).strip()[:1200]} for n, t in enumerate(pages)]}
        for i, pages in pages_by_file.items()
    ]
    return "HỒ SƠ:\n" + json.dumps(payload, ensure_ascii=False)


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    ocr_documents = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TÀI LIỆU:\n"
        f"{json.dumps(ocr_documents, ensure_ascii=False)}\n\n"
        "Hãy phân loại từng tài liệu chỉ theo ocrText."
    )
