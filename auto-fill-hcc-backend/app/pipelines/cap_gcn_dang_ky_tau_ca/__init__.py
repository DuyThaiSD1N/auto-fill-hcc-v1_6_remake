"""Pipeline "Cấp giấy chứng nhận đăng ký tàu cá, tàu phục vụ nuôi trồng thủy sản" — cổng Nông nghiệp &
Môi trường dichvucongnnmt.mae.gov.vn (Form.io).

CÙNG nền tảng Form.io + engine (fillFormStandard dom-* + attach attp-row) và field-key nhân thân
data[...] TRÙNG KHÍT #66 (cap_van_ban_chap_thuan_tau_ca) / #92 / #101.

Form Bước 1:
- Phần I (người nộp) / Phần II (chủ tàu = chủ hồ sơ) — nhân thân 2 vai.
- Phần III — sub-form "1.003650_M2a.H38" (TỜ KHAI ĐĂNG KÝ TÀU CÁ), cổng thêm vào 09/2026: kính gửi, người
  đứng khai (= chủ tàu), thông số tàu, EDITGRID máy chính + chủ sở hữu, đại diện chủ tàu. Key
  data[fullname/address/identityNumber/phoneNumber] TRÙNG Phần I → Phần I occurrence=0, tờ khai occurrence=1.
- Có 3 ĐỐI TƯỢNG (data[chonDoiTuong]): "Cá nhân" / "Tổ chức/Doanh nghiệp" / "Cơ quan nhà nước" — toggle
  ẩn/hiện data[organization]+data[taxCode] (Phần I) và data[ownerOrganizationFullname]+data[ownerTaxCode]
  (Phần II). Bản này TEST đầy đủ nhánh CÁ NHÂN; nhánh Tổ chức/Cơ quan implement theo mapping nhưng CHƯA
  test (không có hồ sơ tổ chức mẫu).

⚠ ĐẶC THÙ MAE (giống #66): ô data[isOwnerDossierCheck] mặc định CHƯA tick. Nên:
  · Tự nộp → CHỦ ĐỘNG TICH (True) để cổng tự nhân bản Phần I → Phần II (KHÔNG điền owner_*).
  · Nộp thay → để CHƯA tick (False) + điền owner_* = chủ tàu tường minh.

⚠ CHỦ TÀU = chủ MỚI (bên B/bên mua Hợp đồng mua bán, người đứng tên Tờ khai 02a.ĐKT) — KHÔNG lấy chủ CŨ
đứng tên trên Giấy chứng nhận đăng ký tàu cá cũ (bên bán).

Đính kèm (Bước 2): bảng 16 dòng thành phần hồ sơ (attp-row). Dòng lồng nhau (GCN xóa đăng ký 3/8/13,
Ảnh tàu 6/12, Tờ khai 02a 5/16) disambiguate bằng componentIndex. CCCD chỉ đối chiếu, KHÔNG có dòng → skip.
"""
