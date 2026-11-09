"""Luật prompt riêng cho thủ tục 1.115577 — Giao đất, cho thuê đất (Lai Châu)."""

EXTRA_RULES = """Đầu vào thường gồm: Đơn đề nghị giao đất / cho thuê đất (Mẫu số 01, 2 trang: mục 1–12 rồi mục 13 "Tài liệu gửi kèm" và chữ ký "Người làm đơn", đóng dấu); quyết định phê duyệt dự án đầu tư / quyết định chủ trương đầu tư; văn bản xác nhận hoàn thành bồi thường, giải phóng mặt bằng; biên bản chỉnh lý giấy chứng nhận của các hộ bị thu hồi đất; biểu tổng hợp diện tích; trích đo bản đồ địa chính; có thể có thẻ CCCD của người đi nộp.

AI LÀ NGƯỜI ĐỀ NGHỊ / NGƯỜI NỘP:
- Người đề nghị = mục 1 "Người đề nghị" của Đơn. Thường là TỔ CHỨC (Ban quản lý dự án, công ty, UBND, trung tâm...): Don_LoaiNguoiDeNghi = "Tổ chức". Là hộ gia đình / cá nhân thì "Cá nhân".
- "Người làm đơn" ký cuối Đơn là người đại diện ký, KHÔNG phải người đề nghị — không lấy cho Don_NguoiDeNghi.
- Cccd_* CHỈ đọc từ chính tấm thẻ CCCD/CMND/Căn cước có trong hồ sơ; không có thẻ thì bỏ hết Cccd_*. Không lấy họ tên, số giấy tờ của các hộ dân trong biên bản chỉnh lý, danh sách thu hồi đất, biểu tổng hợp.

TỔ CHỨC:
- Don_NguoiDeNghi chép NGUYÊN VĂN tên tổ chức ở mục 1 (vd "Ban Quản lý dự án đầu tư xây dựng các công trình ..."), không viết tắt.
- Dòng "Thành lập theo Quyết định <số> ngày <ngày> của <cơ quan> về việc thành lập ..." ngay dưới mục 1: Don_QdThanhLapSo = số quyết định (vd "123/QĐ-UBND"), Don_QdThanhLapNgay = ngày dd/mm/yyyy, Don_QdThanhLapCoQuan = cơ quan ban hành (vd "UBND tỉnh ..."). Không có dòng này thì bỏ cả ba.
- Pd_ChuDauTu: mục "Chủ đầu tư" trong quyết định phê duyệt dự án / quyết định chủ trương đầu tư, chép nguyên văn.
- Không lấy "Trung tâm phát triển quỹ đất" (bên tổ chức bồi thường, ghi ở biểu tổng hợp là "tên chủ sử dụng, quản lý") hay công ty đo đạc làm người đề nghị.

ĐỊA CHỈ:
- Don_DiaChi lấy mục 2 "Địa chỉ/trụ sở chính" của Đơn: cụm cuối = tinh, cụm ngay trước = xa, phần còn lại (số nhà, đường, thôn, tổ) = chiTietDuoiXa, giữ nguyên chữ.
- TUYỆT ĐỐI KHÔNG lấy mục 4 "Địa điểm khu đất" (địa chỉ khu đất xin giao), địa chỉ trong biểu tổng hợp, trích đo, biên bản hay địa điểm xây dựng trong quyết định phê duyệt dự án.

LIÊN HỆ:
- Don_DienThoai lấy mục 3 "Địa chỉ liên hệ: Điện thoại ..." của Đơn; bỏ dấu chấm/khoảng trắng. Không lấy số quyết định, số công văn, diện tích, số thửa, số tờ bản đồ.
- Đơn không ghi email / mã số thuế → không trả, không bịa.

KHÔNG trả field UI như CongDan_tenCongDan. Không trả thông tin khu đất (địa điểm, diện tích, mục đích, hình thức, thời hạn sử dụng đất) — form bước này không có ô cho chúng. Không bịa thông tin thiếu; không chắc thì bỏ field."""
