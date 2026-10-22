"""Prompt đặc thù cho "Cấp Chứng chỉ hành nghề luật sư (miễn đào tạo, miễn tập sự)" (1.000688)."""

EXTRA_RULES = """Thủ tục: Cấp Chứng chỉ hành nghề luật sư đối với người được miễn đào tạo nghề luật sư, miễn tập sự
hành nghề luật sư (Bộ Tư pháp). Tờ khai trên cổng là "Văn bản đề nghị cấp/cấp lại Chứng chỉ hành nghề luật sư":
Kính gửi; nhân thân người đề nghị (họ tên, giới tính, ngày sinh, quốc tịch, nơi thường trú, nơi ở hiện tại, điện
thoại, email, giấy tờ tùy thân số/ngày cấp/nơi cấp); tập sự hoặc lý do miễn tập sự; đề nghị cấp lại; bảng quá trình
hoạt động từ khi đủ 18 tuổi; khen thưởng kỷ luật; bị truy cứu trách nhiệm hình sự; địa danh, ngày làm đơn.

Hồ sơ thường gồm:
- VĂN BẢN ĐỀ NGHỊ CẤP CHỨNG CHỈ HÀNH NGHỀ LUẬT SƯ bản giấy đã ký (nguồn chính của mọi mục tờ khai, bảng quá trình
  hoạt động có thể kéo sang trang 2).
- Phiếu lý lịch tư pháp số 1 và/hoặc số 2 (họ tên, ngày sinh, giới tính, quốc tịch, CCCD số/ngày cấp/nơi cấp, nơi
  thường trú, nơi ở hiện nay, tình trạng án tích). Phiếu số 2 còn ghi cha/mẹ/vợ chồng — KHÔNG lấy làm người đề nghị.
- Bằng cử nhân/thạc sĩ luật, chứng chỉ nghiệp vụ; các quyết định bổ nhiệm chức danh tư pháp; quyết định xuất ngũ.
- Có thể có CCCD.

NGUỒN VÀ ƯU TIÊN:
- Họ tên, ngày sinh, giới tính, số định danh, ngày cấp, nơi cấp: CCCD > Phiếu LLTP > Văn bản đề nghị > quyết định/bằng.
  Quyết định bổ nhiệm thường chỉ ghi "sinh năm" — không dùng khi đã có ngày sinh đầy đủ.
- Nơi thường trú: CCCD > Phiếu LLTP > đơn (Phiếu ghi "Tổ 18hcb" còn đơn ghi "Tổ 18" thì lấy theo Phiếu).
- Nơi ở hiện tại: Ndn_NoiOHienTai theo ĐƠN; đồng thời trả LLTP_NoiOHienNay theo Phiếu để hệ thống đối chiếu.
- Địa chỉ "Số 5 đường A, phường B, thành phố C" → {quocGia:"Việt Nam", tinh:"Thành phố C", xa:"Phường B",
  chiTietDuoiXa:"Số 5 đường A"}; "P." là "Phường", "TP." là "Thành phố". Không có cấp huyện.
- Lý do miễn tập sự, khen thưởng kỷ luật, truy cứu trách nhiệm hình sự: chép nguyên văn phần người làm đơn khai, KHÔNG
  chép phần hướng dẫn in nghiêng trong ngoặc của mẫu.
- QuaTrinh: đủ mọi dòng bảng, đúng thứ tự, mỗi ô chép nguyên văn; ngày "5/9/1999" → "05/09/1999".
- Mọi ngày dd/mm/yyyy. Không bịa điện thoại, email hay dữ liệu giấy tờ không ghi.

KHÔNG trả field UI của eForm (HoVaTenC, TT_TinhThanhC, HoSo_*…). Chỉ trả field compact trong schema."""
