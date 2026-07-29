"""Pipeline "Giải quyết chế độ người hoạt động kháng chiến giải phóng dân tộc, bảo vệ Tổ quốc và
làm nghĩa vụ quốc tế" (MaTTHC 2.009383 — cổng Bộ Nội vụ dichvucongbnv.moha.gov.vn).

Cùng nền tảng Form.io + engine content.js `fillFormStandard` (comp dom-*) như các thủ tục MOHA khác
(uu_dai_ncc_tu_tran, tro_cap_tho_cung_liet_si...). Đối tượng HĐKC = chủ hồ sơ (thường CÒN SỐNG, tự
đứng khai). Điền Phần II (chủ hồ sơ) + Phần IV Mục 1 (occurrence 1); Phần V Mục 2 (đại diện thân nhân)
chỉ khi đối tượng đã chết → để trống. Checkbox data[isOwnerDossierCheck] mặc định TÍCH (khoá Phần II)
→ BỎ TÍCH để mở và điền chủ hồ sơ. Đính kèm 3 thành phần (Bản khai Mẫu 11 / Giấy báo tử / Huân-Huy
chương KC) qua engine attach MOHA (nút "Chọn tệp").
"""
