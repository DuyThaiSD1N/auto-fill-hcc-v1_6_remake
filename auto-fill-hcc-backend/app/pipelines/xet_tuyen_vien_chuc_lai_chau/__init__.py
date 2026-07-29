"""Pipeline "Thủ tục xét tuyển Viên chức (Nghị định số 85/2023/NĐ-CP) (Lai Châu)" (mã 3.000601).

Cổng dichvucong.laichau.gov.vn — eForm chuẩn iGate (field name="CongDan_*", id="_fc*", dropdown
Semantic UI). Engine content.js `fillFormStandard` xử lý sẵn (biến thể tên CongDan_, tra _fc id,
dropdown .ui.selection.dropdown) — CÙNG nền tảng với các thủ tục đất đai Lai Châu (dinh_chinh_sai_sot,
dang_ky_dat_dai...). KHÁC thủ tục `xet_tuyen_vien_chuc` cũ (đó là Form.io data[...]).

Form CHỈ thu 25 field NGƯỜI NỘP = người dự tuyển (block CongDan_*). Toàn bộ chi tiết dự tuyển (đào tạo,
gia đình, quá trình công tác, nguyện vọng) nằm TRONG Phiếu đăng ký dự tuyển Mẫu 01 đính kèm, không
nhập e-form. Đính kèm 1 thành phần: Phiếu Mẫu 01 (Bản chính).
"""
