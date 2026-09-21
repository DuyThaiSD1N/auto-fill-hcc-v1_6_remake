"""Prompt phân loại đính kèm cho [Lào Cai] Chuyển mục đích sử dụng đất cấp phường/xã (1.115679)."""

import json
from typing import Any

from .catalog import llm_options

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Chuyển mục đích sử dụng đất; chuyển hình thức sử dụng đất; gia
hạn sử dụng đất khi hết thời hạn sử dụng đất; điều chỉnh thời hạn sử dụng đất của dự án đầu tư" nộp tại
UBND phường/xã trên cổng dịch vụ công tỉnh Lào Cai.
</persona>

<danh_muc_nhan>
{llm_options()}
</danh_muc_nhan>

<critical_rules>
1. Chỉ phân loại theo OCR_TEXT. KHÔNG dùng tên file, KHÔNG dùng thứ tự file.
2. Mỗi tài liệu trả ĐÚNG MỘT nhãn trong danh mục (trường "label").
3. Đơn: xác định theo TIÊU ĐỀ và SỐ MẪU — "Mẫu số 02. Đơn đề nghị chuyển mục đích sử dụng đất" →
   "don_mau_02"; chuyển hình thức (Mẫu số 03) → "don_mau_03"; gia hạn (Mẫu số 17) → "don_mau_17".
4. ⚠ HỒ SƠ THỦ TỤC NÀY HAY QUÉT GỘP NHIỀU GIẤY TỜ VÀO MỘT TỆP. Chọn nhãn theo GIẤY TỜ CHÍNH — giấy tờ mà
   tệp đó được nộp để chứng minh, thường đứng đầu tệp:
   - Tệp gồm Quyết định cho phép chuyển mục đích rồi đến quyết định ĐIỀU CHỈNH quyết định đó (và danh sách
     các hộ) → "quyet_dinh_giao_dat".
   - Tệp gồm Phiếu chuyển thông tin + Thông báo thuế + Giấy nộp tiền + Phiếu đo đạc → "ho_so_nghia_vu_tai
     _chinh" nếu phần nghĩa vụ tài chính đứng đầu, "ho_so_do_dac" nếu chỉ có giấy tờ đo đạc.
5. Phân biệt các loại hay nhầm:
   - "GIẤY CHỨNG NHẬN QUYỀN SỬ DỤNG ĐẤT…" (sổ đỏ/sổ hồng) → "gcn"; "GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP"
     → "gcn_dkdn".
   - "QUYẾT ĐỊNH v/v cho phép chuyển mục đích sử dụng đất", "QUYẾT ĐỊNH v/v điều chỉnh Quyết định số …" →
     "quyet_dinh_giao_dat"; KHÔNG phải "gcn".
   - "GIẤY UỶ QUYỀN" có lời chứng công chứng viên → "vb_uy_quyen"; KHÔNG phải "khac".
   - "THÔNG BÁO KẾT QUẢ GIẢI QUYẾT THỦ TỤC HÀNH CHÍNH" của Bộ phận Một cửa → "tb_ket_qua_tthc".
6. Không nhận biết được thì "khac". Trả về DUY NHẤT một JSON object, không giải thích, không markdown.
</critical_rules>

<document_name_rules>
- documentName: tên tiếng Việt ngắn gọn theo nội dung (vd "Đơn đề nghị chuyển mục đích ông Hoàng Trung
  Thành", "GCN QSDĐ số CM 832513 thửa 241", "QĐ 5334/QĐ-UBND và QĐ 386/QĐ-UBND", "Giấy uỷ quyền số
  488/2026/CCGD"), tối đa khoảng 60 ký tự. Nhiều tài liệu cùng loại → tên khác nhau. OCR quá thiếu thì để
  trống.
</document_name_rules>

<output_contract>
{{"documents":[{{"index":0,"label":"don_mau_02","documentName":"Đơn đề nghị chuyển mục đích ông Hoàng Trung Thành"}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    rows = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return (
        "DANH SÁCH OCR_TEXT CỦA TỪNG TÀI LIỆU:\n"
        f"{json.dumps(rows, ensure_ascii=False)}\n\n"
        "Gán nhãn cho từng tài liệu chỉ theo ocrText, theo giấy tờ CHÍNH của tệp."
    )
