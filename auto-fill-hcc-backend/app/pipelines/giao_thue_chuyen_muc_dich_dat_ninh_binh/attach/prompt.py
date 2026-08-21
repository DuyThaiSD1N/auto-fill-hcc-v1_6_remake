"""Prompt LLM-first phân loại 16 dòng thành phần hồ sơ Ninh Bình."""

import json
from typing import Any


SYSTEM_PROMPT = """
Bạn phân loại từng OCR_TEXT cho thủ tục giao đất/cho thuê đất/chuyển mục đích sử dụng đất/gia hạn sử
dụng đất tại Ninh Bình. Chỉ dùng OCR_TEXT, không dùng tên hoặc thứ tự file.

Mỗi tài liệu trả đúng một docType:
- ket_qua_lua_chon_nha_dau_tu: văn bản phê duyệt kết quả lựa chọn nhà đầu tư theo khoản 2 Điều 116.
- don_mau_01: Đơn theo Mẫu số 01.
- van_ban_phe_duyet_dau_tu: phê duyệt dự án/chấp thuận chủ trương đầu tư/PPP.
- gcn: Giấy chứng nhận QSDĐ/sổ đỏ/sổ hồng hoặc quyết định giao/cho thuê/chuyển mục đích đất.
- phuong_an_tang_dat_mat: Phương án sử dụng tầng đất mặt Mẫu số 26.
- du_an_giao_rung: dự án đầu tư khu rừng + báo cáo/bản đồ hiện trạng rừng.
- dau_gia_thue_rung: kết quả/biên bản/danh sách trúng đấu giá thuê rừng.
- giay_to_dau_tu_tong_hop: nhóm văn bản đầu tư, chấp thuận nhà đầu tư, đấu giá không thành, nhận chuyển nhượng dự án.
- phuong_an_cong_ty_nong_lam: phương án sử dụng đất của công ty nông, lâm nghiệp tại địa phương.
- phuong_an_dat_thu_hoi: phương án sử dụng diện tích đất thu hồi của công ty nông, lâm nghiệp.
- phuong_an_to_chuc_kinh_te: phương án sử dụng đất của tổ chức kinh tế/đơn vị sự nghiệp công lập.
- don_mau_04: ĐƠN XIN GIA HẠN SỬ DỤNG ĐẤT Mẫu số 04.
- uy_quyen: văn bản/hợp đồng ủy quyền hoặc đại diện thực hiện thủ tục.
- cccd: căn cước/CMND/hộ chiếu.
- other: không đủ bằng chứng.

Ưu tiên tiêu đề và cấu trúc thật của tài liệu. Đơn có nhắc Giấy chứng nhận vẫn là don_mau_04 hoặc
don_mau_01; Giấy chứng nhận thật có số phát hành, số vào sổ, thửa đất/tờ bản đồ là gcn.
Trả duy nhất JSON: {"documents":[{"index":0,"docType":"gcn"}]}
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "DANH SÁCH OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False)
