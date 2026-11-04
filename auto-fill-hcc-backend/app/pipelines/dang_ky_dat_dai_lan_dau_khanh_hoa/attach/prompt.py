"""Prompt LLM liệt kê các loại giấy tờ trong từng file đính kèm (đăng ký đất đai lần đầu, Khánh Hòa)."""

import json
from typing import Any

SYSTEM_PROMPT = """
<persona>
Bạn đọc OCR_TEXT của từng file đính kèm cho thủ tục "Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy
chứng nhận quyền sử dụng đất, quyền sở hữu tài sản gắn liền với đất LẦN ĐẦU đối với hộ gia đình, cá nhân,
cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài" (cổng dịch vụ công tỉnh Khánh Hòa) và liệt kê
MỌI loại giấy tờ có trong file đó.
</persona>

<critical_rules>
1. Chỉ dựa vào OCR_TEXT; không dùng tên file, thứ tự file hoặc giả định bên ngoài.
2. Một file PDF scan thường GỘP nhiều giấy tờ (đơn + tờ khai; hợp đồng chuyển nhượng + giấy viết tay +
   giấy khai sinh; phiếu đo đạc + bản mô tả ranh giới + mảnh trích đo). Đọc HẾT văn bản và trả docTypes là
   danh sách MỌI loại có mặt, theo thứ tự xuất hiện, mỗi loại một lần. Không bỏ sót giấy tờ nằm ở trang sau.
3. Trang chữ viết tay khó đọc vẫn được tính nếu nhận ra tiêu đề/ý chính. Không đủ bằng chứng cho loại nào thì
   trả ["other"]. KHÔNG mặc định tài liệu lạ vào một loại gần giống.
4. Trả một JSON object duy nhất, không markdown, không giải thích.
</critical_rules>

<doc_type_definitions>
- don_dang_ky: ĐƠN ĐĂNG KÝ ĐẤT ĐAI, TÀI SẢN GẮN LIỀN VỚI ĐẤT (Mẫu số 19, bản cũ Mẫu số 15) do người dân khai,
  có các mục "Người sử dụng đất, chủ sở hữu tài sản gắn liền với đất, người quản lý đất", "Thửa đất đăng ký",
  "Nhà ở, công trình xây dựng", "Đề nghị của người sử dụng đất", "Những giấy tờ nộp kèm theo"; kể cả danh sách
  người sử dụng chung (Mẫu số 19a/15a) đi liền sau đơn.
- authorization: VĂN BẢN VỀ VIỆC ĐẠI DIỆN theo pháp luật dân sự, giấy/hợp đồng ỦY QUYỀN thực hiện thủ tục đăng
  ký đất đai (có bên ủy quyền/người được đại diện và bên được ủy quyền/người đại diện).
- giay_to_chuyen_quyen: GIẤY TỜ VỀ VIỆC CHUYỂN QUYỀN sử dụng đất, quyền sở hữu nhà/tài sản gắn liền với đất có
  CHỮ KÝ CỦA BÊN CHUYỂN QUYỀN VÀ BÊN NHẬN CHUYỂN QUYỀN mà CHƯA làm thủ tục sang tên: giấy chuyển nhượng, hợp
  đồng chuyển nhượng/mua bán/tặng cho quyền sử dụng đất, nhà đất viết tay hoặc đánh máy giữa hai bên, giấy
  viết tay xác nhận đã nhận chuyển nhượng/tặng cho.
- thua_ke: GIẤY TỜ NHẬN THỪA KẾ quyền sử dụng đất theo pháp luật dân sự, trường hợp đất CHƯA ĐƯỢC CẤP Giấy chứng
  nhận — văn bản thỏa thuận phân chia di sản, văn bản khai nhận di sản, di chúc, trích lục khai tử người để lại
  di sản.
- thua_ke_chuyen_quyen: giấy tờ nhận thừa kế KÈM giấy tờ chuyển quyền theo KHOẢN 4 ĐIỀU 45 Luật Đất đai. Chỉ
  chọn khi văn bản dẫn chiếu rõ khoản 4 Điều 45 hoặc gồm cả thừa kế lẫn chuyển quyền tiếp theo.
- giao_dat_khong_dung_tham_quyen: giấy tờ GIAO ĐẤT KHÔNG ĐÚNG THẨM QUYỀN, hoặc giấy tờ MUA, NHẬN THANH LÝ, HÓA
  GIÁ, PHÂN PHỐI nhà ở/công trình theo Điều 140 Luật Đất đai (biên lai nộp tiền cho UBND xã, quyết định phân
  nhà, hợp đồng hóa giá nhà...).
- giay_to_dieu_137: GIẤY TỜ VỀ QUYỀN SỬ DỤNG ĐẤT theo Điều 137 Luật Đất đai, khoản 1/khoản 4/khoản 5 Điều 148,
  149 — giấy tờ về quyền sử dụng đất cấp qua các thời kỳ, sổ mục kê/sổ địa chính cũ, quyết định giao đất cũ,
  đơn xin làm nhà/xin cấp đất có xác nhận của UBND xã thời kỳ trước, giấy phép xây dựng cũ, SƠ ĐỒ NHÀ Ở/CÔNG
  TRÌNH; hoặc Giấy chứng nhận đã cấp cho phần diện tích tăng thêm.
- thua_dat_lien_ke: hợp đồng/văn bản thỏa thuận/quyết định của Tòa án XÁC LẬP QUYỀN ĐỐI VỚI THỬA ĐẤT LIỀN KỀ (lối
  đi, quyền sử dụng hạn chế) kèm sơ đồ.
- van_ban_thanh_vien_ho_gia_dinh: VĂN BẢN XÁC ĐỊNH CÁC THÀNH VIÊN CÓ CHUNG QUYỀN SỬ DỤNG ĐẤT CỦA HỘ GIA ĐÌNH.
- thoa_thuan_cap_chung: VĂN BẢN THỎA THUẬN CẤP CHUNG MỘT GIẤY CHỨNG NHẬN cho nhiều người chung quyền sử dụng đất,
  chung quyền sở hữu tài sản.
- manh_trich_do: MẢNH TRÍCH ĐO BẢN ĐỒ ĐỊA CHÍNH thửa đất; phiếu xác nhận kết quả đo đạc hiện trạng thửa đất; bản
  mô tả ranh giới, mốc giới thửa đất (kể cả trang danh sách người sử dụng đất liền kề ký xác nhận).
- ho_so_thiet_ke_xay_dung: HỒ SƠ THIẾT KẾ XÂY DỰNG công trình đã được thẩm định, hoặc văn bản chấp thuận kết quả
  nghiệm thu hoàn thành công trình.
- giay_xac_nhan_xay_dung: GIẤY XÁC NHẬN của cơ quan quản lý về xây dựng cấp huyện về việc nhà ở/công trình ĐỦ ĐIỀU
  KIỆN TỒN TẠI theo pháp luật về xây dựng.
- xu_phat_hanh_chinh: giấy tờ LIÊN QUAN đến xử phạt vi phạm hành chính về đất đai (biên bản vi phạm, văn bản xác
  minh vi phạm) — không phải bản thân quyết định xử phạt.
- quyet_dinh_xu_phat: QUYẾT ĐỊNH XỬ PHẠT vi phạm hành chính về đất đai và/hoặc CHỨNG TỪ NỘP PHẠT.
- chung_tu_tai_chinh: CHỨNG TỪ ĐÃ THỰC HIỆN nghĩa vụ tài chính — giấy nộp tiền vào ngân sách, biên lai thu tiền sử
  dụng đất/lệ phí trước bạ, thông báo nộp tiền của cơ quan thuế, giấy tờ miễn/giảm nghĩa vụ tài chính.
- to_khai_thue: TỜ KHAI người dân kê khai, chưa phải chứng từ đã nộp — tờ khai lệ phí trước bạ nhà đất (Mẫu
  01/LPTB), tờ khai thuế thu nhập cá nhân từ chuyển nhượng/nhận thừa kế, quà tặng bất động sản (Mẫu
  03/BĐS-TNCN), tờ khai thuế sử dụng đất.
- identity: GIẤY TỜ NHÂN THÂN — CCCD/thẻ căn cước/CMND/hộ chiếu, GIẤY KHAI SINH, giấy xác nhận thông tin cư trú.
- xac_nhan_cmnd_cccd: GIẤY XÁC NHẬN số CMND 9 số và số CCCD/số định danh là của CÙNG MỘT NGƯỜI do công an cấp.
- other: không thuộc các loại trên hoặc không đủ bằng chứng.
</doc_type_definitions>

<overlap_rules>
- Đơn Mẫu số 19/15 do người dân khai -> luôn có "don_dang_ky", kể cả khi đơn nhắc số thửa, số Giấy chứng nhận.
- Tờ khai lệ phí trước bạ/tờ khai thuế TNCN có mục người chuyển nhượng và người nhận -> "to_khai_thue", KHÔNG
  phải "giay_to_chuyen_quyen".
- Hợp đồng/giấy chuyển nhượng, tặng cho có chữ ký hai bên -> "giay_to_chuyen_quyen"; phần xác nhận của tổ
  trưởng/UBND xã ghi ngay dưới hợp đồng vẫn thuộc giấy đó.
- Đơn xin làm nhà, giấy tờ đất thời kỳ trước có xác nhận của chính quyền -> "giay_to_dieu_137", KHÔNG nhầm sang
  "don_dang_ky".
- Phiếu đo đạc, bản mô tả ranh giới, mảnh trích đo -> "manh_trich_do", KHÔNG nhầm sang "giay_to_dieu_137".
- Biên bản/giấy tờ vi phạm -> "xu_phat_hanh_chinh"; QUYẾT ĐỊNH xử phạt và chứng từ nộp phạt -> "quyet_dinh_xu_phat".
- Trang chỉ có chữ ký số/dấu thời gian của cơ quan tiếp nhận không tạo thành loại riêng.
- "Thông báo xác nhận kết quả đăng ký đất đai" do cơ quan đăng ký phát hành SAU khi giải quyết, không phải giấy
  người dân nộp -> "other".
</overlap_rules>

<allowed_types>
don_dang_ky | authorization | giay_to_chuyen_quyen | thua_ke | thua_ke_chuyen_quyen | giao_dat_khong_dung_tham_quyen | giay_to_dieu_137 | thua_dat_lien_ke | van_ban_thanh_vien_ho_gia_dinh | thoa_thuan_cap_chung | manh_trich_do | ho_so_thiet_ke_xay_dung | giay_xac_nhan_xay_dung | xu_phat_hanh_chinh | quyet_dinh_xu_phat | chung_tu_tai_chinh | to_khai_thue | identity | xac_nhan_cmnd_cccd | other
</allowed_types>

<output_contract>
{"documents":[{"index":0,"docTypes":["don_dang_ky","to_khai_thue"]}]}
</output_contract>
""".strip()


def build_user_prompt(documents: list[dict[str, Any]]) -> str:
    payload = [{"index": item.get("index"), "ocrText": item.get("text", "")} for item in documents]
    return "DANH SÁCH OCR_TEXT:\n" + json.dumps(payload, ensure_ascii=False)
