"""Prompt phân loại đính kèm cho [Lào Cai] 1.013833 — đăng ký biến động đổi tên, thay đổi thông tin người SDĐ."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Đăng ký biến động đối với trường hợp đổi tên hoặc thay đổi thông tin
về người sử dụng đất, chủ sở hữu tài sản gắn liền với đất hoặc thay đổi số hiệu hoặc địa chỉ của thửa đất; thay
đổi hạn chế quyền…; giảm diện tích thửa đất do sạt lở tự nhiên" (mã 1.013833) trên cổng dịch vụ công tỉnh Lào
Cai. Hồ sơ điển hình: Đơn đăng ký biến động, Giấy chứng nhận đã cấp, văn bản cam kết của các thành viên hộ gia
đình, giấy tờ chứng minh việc đổi tên/đổi thông tin.
</persona>

<danh_muc_nhan>
- don_bien_dong: "ĐƠN ĐĂNG KÝ BIẾN ĐỘNG ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT" (Mẫu số 24 hoặc Mẫu số 18 NĐ
  151/2025) — mục "1. Người sử dụng đất…", "2. Nội dung biến động", "3. Giấy tờ liên quan…", "Người viết đơn".
- gcn: GIẤY CHỨNG NHẬN quyền sử dụng đất (quyền sở hữu nhà ở / tài sản gắn liền với đất) ĐÃ CẤP — sổ đỏ/sổ
  hồng, kể cả bản sao chứng thực và "TRANG BỔ SUNG GIẤY CHỨNG NHẬN": bìa "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT" +
  số phát hành, mục "I. Người sử dụng đất", "II. Thửa đất…", "III. Sơ đồ thửa đất", "Những thay đổi sau khi
  cấp giấy chứng nhận", "Số vào sổ cấp GCN". KHÔNG phải "Giấy chứng nhận đăng ký doanh nghiệp", KHÔNG phải
  "Giấy chứng nhận kết hôn".
- cam_ket_ho_gia_dinh: VĂN BẢN CAM KẾT / VĂN BẢN THỎA THUẬN "của các thành viên hộ gia đình có chung quyền sử
  dụng đất" (xác nhận thành viên hộ, không có công sức đóng góp, thống nhất để người khác đứng tên), thường kèm
  "LỜI CHỨNG CHỨNG THỰC CHỮ KÝ" của văn phòng công chứng / UBND xã.
- van_ban_cong_nhan: văn bản của CƠ QUAN NHÀ NƯỚC có thẩm quyền cho phép hoặc công nhận việc đổi tên, thay đổi
  thông tin (quyết định cho phép đổi tên, quyết định đổi tên đơn vị, xác nhận thay đổi số hiệu/địa chỉ thửa
  đất, văn bản xác nhận sạt lở tự nhiên…).
- giay_to_doi_ten: giấy tờ CHỨNG MINH việc đổi tên, thay đổi thông tin của người sử dụng đất: giấy khai sinh /
  trích lục cải chính, thay đổi hộ tịch; giấy xác nhận số chứng minh nhân dân cũ – số định danh; giấy xác nhận
  thông tin về cư trú; GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP (thay đổi tên doanh nghiệp).
- cccd: CĂN CƯỚC / CĂN CƯỚC CÔNG DÂN / CMND / hộ chiếu (ảnh chụp hoặc bản photo).
- uy_quyen: GIẤY ỦY QUYỀN / HỢP ĐỒNG ỦY QUYỀN / văn bản về việc đại diện — có dòng "ủy quyền cho".
- manh_trich_do: MẢNH TRÍCH ĐO BẢN ĐỒ ĐỊA CHÍNH thửa đất ("HỆ TỌA ĐỘ VN-2000", "BẢNG THỐNG KÊ TỌA ĐỘ"). Sơ
  đồ thửa in sẵn trong Giấy chứng nhận KHÔNG phải mảnh trích đo.
- thay_doi_quyen_lien_quan: văn bản về việc thay đổi quyền của người có quyền lợi liên quan / quyền đối với
  thửa đất liền kề (thỏa thuận lối đi, cấp thoát nước qua thửa liền kề…), hợp đồng/văn bản thay đổi hạn chế
  quyền sử dụng đất.
- ket_hon: GIẤY CHỨNG NHẬN KẾT HÔN, trích lục kết hôn, giấy xác nhận tình trạng hôn nhân.
- khac: không thuộc các nhãn trên (hóa đơn, biên lai, thông báo thuế…), hoặc OCR quá thiếu để kết luận.
</danh_muc_nhan>

<critical_rules>
1. Chỉ phân loại theo OCR_TEXT. KHÔNG dùng tên file, KHÔNG dùng thứ tự file.
2. Mỗi tài liệu trả ĐÚNG MỘT nhãn trong danh mục.
3. Một file có thể quét gộp nhiều giấy tờ → chọn nhãn theo GIẤY TỜ CHÍNH (trang đầu, tiêu đề lớn nhất). Văn bản
   cam kết kèm lời chứng thực ở trang cuối vẫn là cam_ket_ho_gia_dinh; Giấy chứng nhận kèm trang bổ sung và lời
   chứng thực bản sao vẫn là gcn.
4. Đơn, văn bản cam kết và Giấy chứng nhận đều nhắc số phát hành, số thửa → phân biệt theo TIÊU ĐỀ.
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
