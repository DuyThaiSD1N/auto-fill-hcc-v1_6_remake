"""Prompt phân loại đính kèm cho [Lào Cai] 1.115694 — thửa đất có diện tích tăng thêm."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Đăng ký, cấp Giấy chứng nhận đối với thửa đất có diện tích
tăng thêm do thay đổi ranh giới so với Giấy chứng nhận đã cấp; phần diện tích đất tăng thêm do nhận
chuyển quyền sử dụng một phần thửa đất đã được cấp Giấy chứng nhận" trên cổng dịch vụ công tỉnh Lào Cai.
</persona>

<danh_muc_nhan>
- don_bien_dong: ĐƠN ĐĂNG KÝ BIẾN ĐỘNG đất đai, tài sản gắn liền với đất (Mẫu số 24) — đơn do người sử
  dụng đất ký, có mục "Người sử dụng đất", "Nội dung biến động", "Giấy tờ nộp kèm theo đơn".
- gcn: GIẤY CHỨNG NHẬN quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất ĐÃ CẤP (sổ đỏ/sổ hồng) —
  có số phát hành dạng 2 chữ cái + số, số vào sổ cấp GCN, thửa đất, tờ bản đồ, sơ đồ thửa đất.
  KHÔNG phải "Giấy chứng nhận đăng ký doanh nghiệp".
- giay_to_chuyen_quyen: giấy tờ về việc NHẬN CHUYỂN QUYỀN phần diện tích tăng thêm — hợp đồng mua bán/
  chuyển nhượng/tặng cho/thừa kế/góp vốn quyền sử dụng đất, nhà ở (kể cả các PHỤ LỤC hợp đồng, phụ lục
  điều chỉnh thông tin, danh mục hoàn thiện, bản vẽ mẫu nhà) và BIÊN BẢN BÀN GIAO nhà ở/thửa đất.
- chung_tu_thanh_toan: HÓA ĐƠN giá trị gia tăng, biên lai, ủy nhiệm chi, VĂN BẢN XÁC NHẬN SỐ TIỀN ĐÃ
  THANH TOÁN của bên bán — chứng từ tiền nong của chính giao dịch chuyển quyền nêu trên.
- manh_trich_do: MẢNH TRÍCH ĐO / mảnh đo đạc chỉnh lý BẢN ĐỒ ĐỊA CHÍNH thửa đất, phiếu đo đạc xác định
  lại kích thước - diện tích, do đơn vị đo đạc lập và Văn phòng đăng ký đất đai xác nhận. Sơ đồ thửa đất
  IN SẴN trong Giấy chứng nhận hoặc kèm hợp đồng KHÔNG phải mảnh trích đo.
- van_ban_dai_dien: GIẤY ỦY QUYỀN / HỢP ĐỒNG ỦY QUYỀN / văn bản về việc đại diện theo pháp luật dân sự —
  có dòng "ủy quyền cho", thường kèm lời chứng của công chứng viên.
- to_khai_thue: TỜ KHAI thuế, lệ phí — tờ khai lệ phí trước bạ nhà, đất (Mẫu 01/LPTB), tờ khai thuế sử
  dụng đất phi nông nghiệp (Mẫu 01/TK-SDDPNN), tờ khai thuế thu nhập cá nhân.
- giay_to_nhan_than: CĂN CƯỚC CÔNG DÂN/CMND/thẻ Căn cước, hộ chiếu, giấy chứng nhận kết hôn, giấy khai
  sinh, sổ hộ khẩu — giấy tờ nhân thân/hộ tịch của các bên.
- khac: không thuộc các nhãn trên, hoặc OCR quá thiếu để kết luận.
</danh_muc_nhan>

<critical_rules>
1. Chỉ phân loại theo OCR_TEXT. KHÔNG dùng tên file, KHÔNG dùng thứ tự file.
2. Mỗi tài liệu trả ĐÚNG MỘT nhãn trong danh mục.
3. ⚠ MỘT FILE THƯỜNG QUÉT GỘP NHIỀU GIẤY TỜ. Hãy chọn nhãn theo GIẤY TỜ CHÍNH — là giấy tờ mà file đó
   được nộp để chứng minh, thường chiếm nhiều trang nhất hoặc là giấy tờ có giá trị pháp lý cao nhất:
   - File có hợp đồng mua bán + các phụ lục + biên bản bàn giao → "giay_to_chuyen_quyen".
   - File mở đầu bằng vài trang CCCD/giấy chứng nhận kết hôn rồi tới GIẤY ỦY QUYỀN → "van_ban_dai_dien"
     (giấy ủy quyền là giấy tờ chính; CCCD chỉ đi kèm để đối chiếu).
   - File gồm tờ khai lệ phí trước bạ + tờ khai thuế + ĐƠN ĐĂNG KÝ BIẾN ĐỘNG → "don_bien_dong"
     (đơn là thành phần hồ sơ chính; các tờ khai chỉ nộp kèm).
   - File chỉ có hóa đơn và/hoặc văn bản xác nhận số tiền đã thanh toán → "chung_tu_thanh_toan".
4. Phân biệt kỹ "gcn" (Giấy chứng nhận quyền sử dụng ĐẤT) với "giay_to_nhan_than" và với Giấy chứng nhận
   ĐĂNG KÝ DOANH NGHIỆP (cái sau xếp "khac").
5. Không chắc chắn thì trả "khac" — tuyệt đối không đoán bừa.
6. Trả về DUY NHẤT một JSON object, không giải thích, không markdown.
</critical_rules>

<output_contract>
{"documents":[{"index":0,"docType":"don_bien_dong"}]}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    rows = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TÀI LIỆU:\n"
        f"{json.dumps(rows, ensure_ascii=False)}\n\n"
        "Gán nhãn cho từng tài liệu chỉ theo ocrText, theo giấy tờ CHÍNH của file."
    )
