"""Prompt LLM liệt kê giấy tờ trong TỪNG FILE (chế độ không tách) — "Cấp GCN đủ điều kiện kinh doanh dược (Sở Y tế)".
Định nghĩa loại giấy dùng chung với chế độ tách (dinh_kem_tach/prompt.py chèn nguyên khối DOC_TYPES)."""

import json
from typing import Any

DOC_TYPES = """
   - don_de_nghi: ĐƠN ĐỀ NGHỊ CẤP Giấy chứng nhận đủ điều kiện kinh doanh dược (Mẫu số 10) — "Kính gửi: Sở Y tế",
     "Tên cơ sở", "Loại hình cơ sở kinh doanh", "Phạm vi kinh doanh", người ký "NGƯỜI ĐẠI DIỆN THEO PHÁP LUẬT". Trang
     "Ghi chú: (1) Cơ quan cấp …" cuối Đơn vẫn thuộc Đơn.
   - danh_muc_ho_so: DANH MỤC HỒ SƠ (bảng kê thành phần hồ sơ / tệp đính kèm, "Bảng dữ liệu dùng chung…").
   - tai_lieu_ky_thuat: TÀI LIỆU KỸ THUẬT về cơ sở vật chất, tài liệu chuyên môn kỹ thuật và nhân sự theo nguyên tắc
     Thực hành tốt (GDP / GPP) — điểm b khoản 1 Điều 38 Luật Dược; sơ đồ kho, danh mục SOP, danh sách nhân sự, trang
     thiết bị; tài liệu chứng minh đáp ứng khoản 5 Điều 19 NĐ 163/2025.
   - giay_to_phap_ly: GIẤY CHỨNG NHẬN ĐĂNG KÝ DOANH NGHIỆP / ĐĂNG KÝ HỘ KINH DOANH, hoặc tài liệu pháp lý chứng minh việc
     thành lập cơ sở (quyết định thành lập…).
   - thuyet_minh_an_ninh: TÀI LIỆU THUYẾT MINH cơ sở đáp ứng các biện pháp bảo đảm an ninh, không để thất thoát thuốc
     phải kiểm soát đặc biệt (Mẫu số 11).
   - cchn_duoc: CHỨNG CHỈ HÀNH NGHỀ DƯỢC (văn bản cấp chứng chỉ, số …/CCHN-D-…, vị trí hành nghề). Dòng "Số CCHN Dược"
     chỉ được KÊ trong Đơn / Danh mục thì KHÔNG phải loại này.
   - cccd: thẻ Căn cước / Căn cước công dân / CMND / hộ chiếu (hai mặt cùng một thẻ là một giấy).
   - other: mọi tài liệu khác."""

SYSTEM_PROMPT = f"""
<persona>
Bạn phân loại tài liệu đính kèm cho thủ tục "Cấp Giấy chứng nhận đủ điều kiện kinh doanh dược". Mỗi file có thể gộp
nhiều giấy tờ (OCR_TEXT có thể đánh dấu từng trang). Liệt kê MỌI loại giấy có trong file (docTypes); hệ thống đính
NGUYÊN file, không tách trang.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. docTypes gồm mọi loại giấy có mặt trong file, mỗi loại một lần, theo thứ tự xuất hiện. Loại giấy:{DOC_TYPES}
3. Giấy CHỈ được kê tên trong Danh mục hồ sơ / Đơn (vd bảng "Thành phần hồ sơ", dòng "Số CCHN Dược") KHÔNG phải giấy có
   trong file — phải thấy chính trang giấy đó (tiêu đề + nội dung).
4. documentName: tên giấy chính theo TIÊU ĐỀ in trên giấy, tối đa 50 ký tự, không đuôi tệp; không rõ → "".
5. PHẢI trả đúng một mục cho MỖI fileIndex đầu vào. Không đủ bằng chứng thì trả ["other"].
6. Trả DUY NHẤT một JSON object, không markdown, không giải thích.
</critical_rules>

<output_contract>
{{"documents":[{{"fileIndex":0,"docTypes":["don_de_nghi"],"documentName":"Đơn đề nghị"}},{{"fileIndex":1,"docTypes":["danh_muc_ho_so","tai_lieu_ky_thuat"],"documentName":"Danh mục hồ sơ"}}]}}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"fileIndex": item.get("fileIndex"), "ocrText": item.get("ocrText", "")} for item in documents]
    return "OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False) + "\n\nLiệt kê loại giấy trong từng tài liệu."
