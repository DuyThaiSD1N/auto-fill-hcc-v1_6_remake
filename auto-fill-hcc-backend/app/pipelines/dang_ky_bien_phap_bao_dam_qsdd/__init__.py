"""Pipeline "Đăng ký biện pháp bảo đảm bằng quyền sử dụng đất, tài sản gắn liền với đất" — cổng dịch vụ
công Đà Nẵng dichvucong.danang.gov.vn (Form.io, field-key RIÊNG — khác BYT/MAE).

Form (Bước 1) CHỈ thu NGƯỜI YÊU CẦU ĐĂNG KÝ (nhân thân người nộp/chủ hồ sơ). Toàn bộ nội dung thế chấp
(bên bảo đảm, bên nhận bảo đảm, hợp đồng bảo đảm, mô tả thửa đất/GCN) nằm TRONG Phiếu yêu cầu Mẫu 01a
đính kèm, KHÔNG có trường nhập online.

CHỦ THỂ = người yêu cầu đăng ký = tài khoản đăng nhập (đối chiếu formContext). Có thể là CÁ NHÂN hoặc
TỔ CHỨC (ngân hàng — bên nhận bảo đảm). Nguồn: CCCD + Phiếu Mẫu 01a (Mục 1 họ tên/SĐT/email/địa chỉ liên
hệ; Mục 3.3 hoặc 4.3 số giấy tờ + cơ quan cấp + ngày).

Field-key data[...] cổng Đà Nẵng (RIÊNG): chonDoiTuong, fullname, birthday, gender, identityNumber,
identityDate, identityAgency (nơi cấp — SELECT), nation, province, district, address, phoneNumber, email,
ownerFullname (chủ hồ sơ), isOwnerDossier (checkbox mặc định CHƯA tick), organization, taxCode.

Đính kèm (Bước 2, attp-row 10 dòng): 1 Phiếu 01a / 2 Hợp đồng bảo đảm / 3 GCN (bản gốc) + giấy tờ điều
kiện khác. loaiBan "Bản chính"/"Bản sao" (KHÁC BYT/MAE dùng "Scan tệp tin"). CCCD skip.
"""
