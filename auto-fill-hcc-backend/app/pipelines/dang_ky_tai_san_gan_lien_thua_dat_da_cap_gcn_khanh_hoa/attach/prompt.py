"""Prompt LLM liệt kê các loại giấy tờ trong từng file đính kèm (đăng ký tài sản gắn liền với thửa đất đã cấp GCN,
Khánh Hòa)."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn đọc OCR_TEXT của từng file đính kèm cho thủ tục "Đăng ký tài sản gắn liền với thửa đất đã được cấp Giấy chứng nhận
hoặc đăng ký thay đổi về tài sản gắn liền với đất…" (cổng dịch vụ công tỉnh Khánh Hòa) và liệt kê MỌI loại giấy tờ có
trong file đó.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. Một file PDF scan có thể GỘP nhiều giấy tờ (vd giấy phép xây dựng + hồ sơ thiết kế + bản vẽ mặt bằng; Đơn + CCCD).
   Đọc HẾT văn bản và trả docTypes là danh sách MỌI loại có mặt, theo thứ tự xuất hiện, mỗi loại một lần.
3. Không đủ bằng chứng cho loại nào thì trả ["other"]. KHÔNG mặc định tài liệu lạ vào một loại gần giống.
4. Trả một JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

<doc_type_definitions>
- don_bien_dong: ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT (Mẫu số 18, bản cũ 09/ĐK, 11/ĐK) do người dân
  lập, có "Kính gửi", "Người sử dụng đất, chủ sở hữu tài sản…", "Nội dung biến động", "Người viết đơn".
- gcn: GIẤY CHỨNG NHẬN quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất (sổ đỏ/sổ hồng, kể cả mẫu cũ) đã cấp —
  "Người sử dụng đất…", "Thông tin thửa đất"/"Thửa đất…", "Sơ đồ thửa đất", "Những thay đổi sau khi cấp Giấy chứng
  nhận", "Số vào sổ cấp Giấy chứng nhận", "TRANG BỔ SUNG GIẤY CHỨNG NHẬN".
- giay_to_148_149: giấy tờ về quyền sở hữu nhà ở, công trình xây dựng theo Điều 148, 149 Luật Đất đai: GIẤY PHÉP XÂY
  DỰNG (kể cả trang "Chủ đầu tư phải thực hiện…", "Điều chỉnh/gia hạn giấy phép"), hợp đồng mua bán/tặng cho/thừa kế
  nhà ở, công trình, giấy tờ về sở hữu nhà ở, công trình do cơ quan có thẩm quyền cấp, bản án/quyết định về quyền sở
  hữu nhà ở.
- so_do_nha: SƠ ĐỒ NHÀ Ở, CÔNG TRÌNH XÂY DỰNG đứng riêng (bản vẽ hiện trạng nhà, công trình do đơn vị đo vẽ lập), không
  kèm giấy phép xây dựng.
- ho_so_thiet_ke: HỒ SƠ THIẾT KẾ XÂY DỰNG đã được cơ quan chuyên môn về xây dựng THẨM ĐỊNH, văn bản CHẤP THUẬN KẾT QUẢ
  NGHIỆM THU hoàn thành hạng mục công trình/công trình xây dựng.
- van_ban_gia_han: văn bản CHẤP THUẬN GIA HẠN THỜI HẠN SỞ HỮU NHÀ Ở của tổ chức nước ngoài, cá nhân nước ngoài.
- manh_trich_do: MẢNH TRÍCH ĐO BẢN ĐỒ ĐỊA CHÍNH thửa đất, phiếu đo đạc chỉnh lý thửa đất do đơn vị đo đạc lập.
- authorization: GIẤY/HỢP ĐỒNG ỦY QUYỀN, văn bản về việc đại diện cho người làm thủ tục.
- to_khai_thue: TỜ KHAI LỆ PHÍ TRƯỚC BẠ (01/LPTB), tờ khai thuế thu nhập cá nhân, tờ khai thuế sử dụng đất.
- chung_tu_nop_tien: GIẤY NỘP TIỀN VÀO NGÂN SÁCH NHÀ NƯỚC, biên lai thu thuế/phí/lệ phí (CTT50, CTT55…), thông báo
  nộp thuế.
- identity: CCCD/thẻ căn cước/CMND/hộ chiếu, giấy xác nhận thông tin cư trú.
- other: không thuộc các loại trên hoặc không đủ bằng chứng.
</doc_type_definitions>

<overlap_rules>
- HỒ SƠ THIẾT KẾ XIN PHÉP XÂY DỰNG, bản vẽ (mặt bằng, mặt đứng, mặt cắt, họa đồ vị trí) đóng dấu "GIẤY PHÉP XÂY DỰNG
  số …" đi KÈM giấy phép xây dựng là một phần của "giay_to_148_149". File có cả giấy phép lẫn bản vẽ thì trả
  ["giay_to_148_149", "so_do_nha"]; chỉ thêm "ho_so_thiet_ke" khi có văn bản thẩm định/chấp thuận nghiệm thu thật.
- "Sơ đồ thửa đất, tài sản gắn liền với đất" và bảng tọa độ in TRONG Giấy chứng nhận là "gcn", KHÔNG phải "so_do_nha"
  hay "manh_trich_do".
- Đơn, tờ khai, giấy phép NHẮC số Giấy chứng nhận, số thửa vẫn KHÔNG phải "gcn"; Đơn ghi "Giấy chứng nhận đã cấp; Giấy
  phép xây dựng…" ở mục nội dung chỉ là nhắc tên, không có nghĩa file chứa các giấy đó.
- Số CCCD ghi trong đơn, tờ khai, giấy phép KHÔNG tạo thành "identity"; chỉ trả "identity" khi có chính thẻ/giấy đó.
- Chữ ký thay/thay mặt của cơ quan ("KT. CHỦ TỊCH", "TM. ỦY BAN NHÂN DÂN", "KT. GIÁM ĐỐC"), khối chữ ký số
  ("Người ký:", "Email:", "Cơ quan:", "Thời gian ký:") và dòng "Người được ủy quyền nộp NSNN" của giấy nộp tiền KHÔNG
  phải "authorization".
- Trang trắng, trang chỉ có chữ ký số/dấu thời gian không tạo thành loại riêng.
</overlap_rules>

<allowed_types>
don_bien_dong | gcn | giay_to_148_149 | so_do_nha | ho_so_thiet_ke | van_ban_gia_han | manh_trich_do | authorization | to_khai_thue | chung_tu_nop_tien | identity | other
</allowed_types>

<output_contract>
{"documents":[{"index":0,"docTypes":["giay_to_148_149","so_do_nha"]},{"index":1,"docTypes":["don_bien_dong"]}]}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "DANH SÁCH OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False)
