"""Prompt LLM-first liệt kê giấy tờ trong từng file — giao đất, cho thuê đất, chuyển mục đích (Tuyên Quang)."""

import json
from typing import Any

# Dùng chung cho chế độ tách (dinh_kem_tach/prompt.py).
DOC_TYPE_DEFINITIONS = """
<doc_type>
- don_de_nghi: ĐƠN ĐỀ NGHỊ giao đất/cho thuê đất/CHO PHÉP CHUYỂN MỤC ĐÍCH SỬ DỤNG ĐẤT/giao đất và giao rừng (Mẫu số 01,
  có hoặc không in số mẫu): "Kính gửi", "Người đề nghị", "Địa điểm thửa đất", "Nội dung đề nghị", "Người làm đơn".
- don_gia_han: ĐƠN ĐỀ NGHỊ GIA HẠN SỬ DỤNG ĐẤT (Mẫu số 04).
- gcn: Giấy chứng nhận quyền sử dụng đất / quyền sở hữu nhà ở và tài sản gắn liền với đất (sổ đỏ, sổ hồng) kể cả trang sơ
  đồ thửa đất và "Những thay đổi sau khi cấp"; giấy tờ về quyền sử dụng đất theo Điều 137 Luật Đất đai; quyết định giao
  đất, cho thuê đất, cho phép chuyển mục đích sử dụng đất.
- authorization: GIẤY ỦY QUYỀN / hợp đồng ủy quyền / văn bản đại diện (NGƯỜI ỦY QUYỀN – NGƯỜI ĐƯỢC ỦY QUYỀN), kể cả
  trang "Lời chứng chứng thực chữ ký" in kèm.
- identity: thẻ CCCD/căn cước/CMND, giấy xác nhận số định danh.
- ket_qua_lua_chon_nha_dau_tu: văn bản phê duyệt kết quả lựa chọn nhà đầu tư (khoản 2 Điều 116 Luật Đất đai).
- van_ban_phe_duyet_du_an: văn bản phê duyệt dự án đầu tư, quyết định chấp thuận chủ trương đầu tư / chấp thuận nhà đầu tư.
- giay_to_dau_tu_tong_hop: văn bản chấp thuận nhà đầu tư (khoản 5 Điều 124), kết quả đấu giá quyền sử dụng đất không
  thành, kết quả nhận chuyển nhượng dự án bất động sản, văn bản thu hồi đất theo điểm i khoản 1 Điều 133.
- phuong_an_tang_dat_mat: phương án sử dụng tầng đất mặt (Mẫu số 26) khi chuyển đất chuyên trồng lúa.
- du_an_giao_rung: dự án đầu tư khu rừng đề nghị giao, báo cáo điều tra, bản đồ hiện trạng rừng.
- dau_gia_thue_rung: kết quả/biên bản đấu giá thuê rừng, danh sách người trúng đấu giá thuê rừng.
- phuong_an_cong_ty_nong_lam: phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương.
- phuong_an_dat_thu_hoi: phương án sử dụng diện tích đất thu hồi của công ty nông, lâm nghiệp.
- phuong_an_to_chuc_kinh_te: phương án sử dụng đất của tổ chức kinh tế, đơn vị sự nghiệp công lập.
- other: giấy khác (tờ khai thuế, biên lai, trích đo...) hoặc không đủ bằng chứng.
Một giấy CHỈ được nhắc trong đơn (số Giấy chứng nhận, "Tài liệu gửi kèm") không phải là giấy có trong file — phải thấy
chính trang giấy đó. Đơn có dẫn số Giấy chứng nhận vẫn là don_de_nghi; giấy ủy quyền có dẫn số Giấy chứng nhận vẫn là
authorization.
</doc_type>
""".strip()

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Giao đất, cho thuê đất, chuyển mục đích sử dụng đất …, gia hạn sử dụng đất"
trên cổng dịch vụ công tỉnh Tuyên Quang. Mỗi file có thể gộp nhiều giấy (OCR_TEXT đánh dấu [Trang n]). Liệt kê MỌI loại
giấy có trong file (docTypes).
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. Mỗi file trả docTypes gồm mọi loại giấy có mặt trong file, mỗi loại một lần, theo thứ tự xuất hiện.
3. Không đủ bằng chứng thì trả ["other"]. Trả một JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

{DOC_TYPE_DEFINITIONS}

<output_contract>
{{"documents":[{{"index":0,"docTypes":["don_de_nghi"]}},{{"index":1,"docTypes":["authorization"]}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "DANH SÁCH OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False)
