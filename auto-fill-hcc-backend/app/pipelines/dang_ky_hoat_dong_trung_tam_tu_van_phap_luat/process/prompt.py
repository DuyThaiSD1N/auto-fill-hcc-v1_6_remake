"""Prompt đặc thù cho "Đăng ký hoạt động của Trung tâm tư vấn pháp luật" (1.000627)."""

EXTRA_RULES = """Thủ tục: Đăng ký hoạt động của Trung tâm tư vấn pháp luật (Bộ Tư pháp, nộp tại Sở Tư pháp). Tờ khai trên
cổng là "Đơn đăng ký hoạt động của Trung tâm tư vấn pháp luật" Mẫu TP-TVPL-01-sđ: Kính gửi; tên Trung tâm, quyết định
thành lập (số, ngày, tổ chức chủ quản ban hành); 1. tên đầy đủ, tên viết tắt; 2. địa chỉ trụ sở, điện thoại, fax,
email; 3. Giám đốc Trung tâm (nhân thân, giấy tờ tùy thân, thẻ tư vấn viên / chứng chỉ hành nghề luật sư / thẻ luật
sư); 4. phạm vi hoạt động; 5. danh sách tư vấn viên pháp luật, luật sư, nhân viên; địa danh, ngày ký, người ký.

Hồ sơ thường gồm:
- ĐƠN ĐĂNG KÝ HOẠT ĐỘNG bản giấy (nguồn chính của Kính gửi, tên viết tắt, fax, phạm vi hoạt động, danh sách nhân sự,
  ngày ký).
- QUYẾT ĐỊNH về việc THÀNH LẬP Trung tâm và QUYẾT ĐỊNH về việc CỬ GIÁM ĐỐC của tổ chức chủ quản (thường chung một
  tệp: quyết định thành lập trước, quyết định cử Giám đốc sau).
- DỰ THẢO QUY CHẾ tổ chức, hoạt động của Trung tâm.
- Danh sách / hồ sơ của tư vấn viên pháp luật, luật sư làm việc theo hợp đồng lao động; Danh mục hồ sơ.
- Có thể có CCCD của Giám đốc.

NGUỒN VÀ ƯU TIÊN:
- Thông tin Trung tâm (tên, số/ngày quyết định thành lập, tổ chức chủ quản, trụ sở): Quyết định thành lập > Đơn > Quy
  chế. Hai quyết định cùng tệp: số/ngày của quyết định THÀNH LẬP (văn bản có tiêu đề "Về việc thành lập …"), KHÔNG lấy
  số/ngày của quyết định cử Giám đốc.
- Nhân thân Giám đốc: CCCD > Đơn mục 3 > Quyết định cử Giám đốc. Người ký các quyết định (Chủ tịch tổ chức chủ quản)
  KHÔNG phải Giám đốc.
- Địa chỉ "Số 12, đường A, phường B, tỉnh C" → {quocGia:"Việt Nam", tinh:"Tỉnh C", xa:"Phường B", chiTietDuoiXa:"Số
  12, đường A"}; "P." là "Phường", "TP." là "Thành phố". Không có cấp huyện.
- Ô Đơn ghi "Không" / "Không có" (tên viết tắt, fax, thẻ tư vấn viên) → bỏ, không trả chữ "Không".
- Mọi ngày dd/mm/yyyy. Không bịa điện thoại, email hay dữ liệu giấy tờ không ghi.

KHÔNG trả field UI của eForm (TTTVPL, Hovaten, DCTS_Tinh…). Chỉ trả field compact trong schema."""
