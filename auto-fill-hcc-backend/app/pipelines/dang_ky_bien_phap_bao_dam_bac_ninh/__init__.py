"""Thủ tục "[Bắc Ninh] Đăng ký biện pháp bảo đảm bằng QSDĐ, tài sản gắn liền với đất" (1.011441).

Cổng Liferay Bắc Ninh (dichvucong.bacninh.gov.vn), eForm Phiếu yêu cầu đăng ký Mẫu 01a (NĐ 99/2022).
Cấu trúc 3 phần giống [[xoa_dang_ky_bien_phap_bao_dam_bac_ninh]] (1.011443) NHƯNG lớn hơn nhiều — có
HAI bên (Bên bảo đảm/bên thế chấp = chủ tài sản, cá nhân/tổ chức; Bên nhận bảo đảm = ngân hàng) + Hợp
đồng bảo đảm + mô tả tài sản GCN.

1. ĐƠN (registration_form): điền ~35 ô eForm theo NAME element_478xx (né trùng semantic giữa các mục).
2. ỦY QUYỀN (authorized_person): doiTuongKhac* (fillAuthorizedPersonBacNinh) — chỉ khi có Văn bản ủy quyền.
3. ĐÍNH KÈM: Phiếu 01a→KQ003675, Hợp đồng bảo đảm→KQ003676, GCN gốc→KQ003684, CCCD/GCN ĐKDN/khác→bổ sung.

⚠ ĐỂ USER TỰ TÍCH các checkbox: tư cách người yêu cầu (Bên bảo đảm/Bên nhận), loại giấy tờ pháp lý
(CMND/Mã số thuế — nhãn TRÙNG giữa mục 3 & 4 nên FE không tích đúng bằng nhãn), tài sản 5.1, VNPOST.
"""
