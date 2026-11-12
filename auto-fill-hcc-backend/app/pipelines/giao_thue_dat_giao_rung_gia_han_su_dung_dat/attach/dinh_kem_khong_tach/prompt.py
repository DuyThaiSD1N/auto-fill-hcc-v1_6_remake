"""Prompt LLM-first liệt kê giấy tờ trong từng file — giao đất, cho thuê đất, chuyển mục đích, giao rừng, gia hạn
(1.116366, cổng Lâm Đồng)."""

import json
from typing import Any

# Dùng chung cho chế độ tách (dinh_kem_tach/prompt.py).
DOC_TYPE_DEFINITIONS = """
<doc_type>
- don_de_nghi: ĐƠN ĐỀ NGHỊ giao đất / cho thuê đất / CHO PHÉP CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT / giao đất và giao rừng / gia
  hạn sử dụng đất (Mẫu số 01 Phụ lục VI, có hoặc không in số mẫu): "Kính gửi", "Người đề nghị", "Địa điểm thửa đất",
  "Diện tích đất", "Để sử dụng vào mục đích", "Người làm đơn".
- authorization: GIẤY ỦY QUYỀN / hợp đồng ủy quyền / văn bản đại diện (bên ủy quyền – bên được ủy quyền), kể cả trang
  "Lời chứng chứng thực chữ ký" in kèm.
- identity: thẻ CCCD / căn cước / CMND / hộ chiếu (một hoặc hai mặt, một hoặc nhiều người).
- gcn: Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở và tài sản gắn liền với đất (sổ đỏ, sổ hồng) đã cấp, kể cả
  trang "Sơ đồ thửa đất" và "Những thay đổi sau khi cấp Giấy chứng nhận".
- trich_do: mảnh trích đo / mảnh đo đạc chỉnh lý / trích lục bản đồ địa chính thửa đất (sơ đồ thửa, hệ tọa độ VN-2000,
  bảng tọa độ đỉnh thửa, bảng thống kê diện tích).
- to_khai_le_phi_truoc_ba: tờ khai lệ phí trước bạ nhà, đất.
- to_khai_thue_phi_nong_nghiep: tờ khai thuế sử dụng đất phi nông nghiệp.
- giay_to_nguoi_co_cong: giấy tờ chứng minh thuộc diện người có công với cách mạng được miễn, giảm tiền sử dụng đất.
- quyet_dinh_mien_giam: quyết định / văn bản của UBND tỉnh (hoặc cơ quan được ủy quyền) về miễn, giảm tiền sử dụng đất.
- giay_chung_nhan_dau_tu: Giấy chứng nhận đầu tư / Giấy phép đầu tư / Giấy chứng nhận đăng ký đầu tư.
- xac_nhan_cu_tru: giấy xác nhận thông tin về cư trú (CT07) hoặc thông báo số định danh cá nhân và thông tin công dân
  trong Cơ sở dữ liệu quốc gia về dân cư.
- xac_nhan_ho_ngheo: xác nhận / giấy chứng nhận hộ nghèo của cơ quan có thẩm quyền.
- quyet_dinh_giao_dat: quyết định giao đất của cơ quan nhà nước có thẩm quyền (không phải giao đất tái định cư).
- van_ban_thuc_hien_du_an: văn bản của cơ quan nhà nước có thẩm quyền về việc thực hiện dự án.
- van_ban_de_nghi_mgth: văn bản đề nghị miễn, giảm tiền thuê đất theo mẫu số 01/MGTH (Thông tư 80/2021/TT-BTC).
- quyet_dinh_tai_dinh_cu: quyết định giao đất ở để bố trí tái định cư.
- phe_duyet_du_an_dau_tu: văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư / chấp thuận nhà đầu tư,
  văn bản phê duyệt kết quả lựa chọn nhà đầu tư.
- nang_luc_tai_chinh: tài liệu chứng minh năng lực tài chính (xác nhận số dư, báo cáo tài chính, cam kết cho vay).
- dau_gia_khong_thanh: văn bản về kết quả đấu giá quyền sử dụng đất KHÔNG THÀNH (điểm b khoản 6 Điều 125 Luật Đất đai).
- thu_hoi_dieu_133: văn bản thu hồi đất để giao, cho thuê cho tổ chức sau chia tách, sáp nhập, chuyển đổi mô hình (điểm i
  khoản 1 Điều 133).
- phuong_an_to_chuc_kinh_te: phương án sử dụng đất của tổ chức kinh tế, đơn vị sự nghiệp công lập (Điều 180).
- phuong_an_cong_ty_nong_lam: phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương (Điều 181).
- phuong_an_dat_thu_hoi: phương án sử dụng diện tích đất thu hồi của công ty nông, lâm nghiệp (khoản 2 Điều 181).
- du_an_lan_bien: dự án đầu tư lấn biển / hạng mục lấn biển (Điều 190).
- chuyen_nhuong_du_an_bds: văn bản về kết quả nhận chuyển nhượng dự án bất động sản (khoản 7 Điều 124).
- giay_to_mien_giam: giấy tờ đề nghị miễn, giảm tiền sử dụng đất, tiền thuê đất khác (Phụ lục V QĐ 40/2026/QĐ-UBND).
- bao_cao_hien_trang_rung: báo cáo điều tra, đánh giá hiện trạng rừng và bản đồ hiện trạng rừng (giao đất và giao rừng).
- dau_gia_thue_rung: kết quả / biên bản đấu giá thuê rừng, danh sách người trúng đấu giá thuê rừng, dự án đầu tư khu rừng
  đề nghị thuê (cho thuê đất và cho thuê rừng).
- other: giấy khác (biên lai, hợp đồng, giấy tờ nguồn gốc...) hoặc không đủ bằng chứng.
Một giấy CHỈ được nhắc trong đơn ("Tài liệu gửi kèm", số Giấy chứng nhận) không phải là giấy có trong file — phải thấy chính
trang giấy đó. Đơn dẫn số Giấy chứng nhận vẫn là don_de_nghi; giấy ủy quyền dẫn thông tin thửa đất vẫn là authorization;
mảnh trích đo ghi "Giấy chứng nhận…" ở phần ghi chú vẫn là trich_do.
</doc_type>
""".strip()

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất …; giao đất và giao rừng;
cho thuê đất và cho thuê rừng, gia hạn sử dụng đất" trên cổng dịch vụ công tỉnh Lâm Đồng. Mỗi file có thể gộp nhiều giấy
(OCR_TEXT đánh dấu [Trang n]). Liệt kê MỌI loại giấy có trong file (docTypes).
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. Mỗi file trả docTypes gồm mọi loại giấy có mặt trong file, mỗi loại một lần, theo thứ tự xuất hiện.
3. PHẢI trả đúng một mục cho MỖI index đầu vào. Không đủ bằng chứng thì trả ["other"].
4. Trả một JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

{DOC_TYPE_DEFINITIONS}

<output_contract>
{{"documents":[{{"index":0,"docTypes":["don_de_nghi"]}},{{"index":1,"docTypes":["gcn"]}},{{"index":2,"docTypes":["identity"]}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "DANH SÁCH OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False)
