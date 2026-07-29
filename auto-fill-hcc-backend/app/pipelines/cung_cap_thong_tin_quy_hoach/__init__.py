"""Pipeline "Cung cấp thông tin quy hoạch đô thị và nông thôn".

Cổng Bộ Xây dựng dvc.moc.gov.vn (padsvc/apply-online) — CÙNG nền tảng Form.io với các thủ tục
Lâm Đồng: ô data[...] comp dom-*, select Choices.js, ngày flatpickr, engine content.js
`fillFormStandard`. URL không có maThuTucHanhChinh → detect theo ObjectId apply-online riêng.

KHÁC các thủ tục đất đai Lâm Đồng: form CHỈ thu THÔNG TIN NGƯỜI NỘP HỒ SƠ (Phần I) — không có
khối chủ hồ sơ / thửa đất / GCN. Thông tin thửa đất (thửa, tờ bản đồ, diện tích, số GCN...) nộp
qua BẢN SCAN Đơn đề nghị + Giấy chứng nhận ở bước đính kèm, không có ô riêng trên form.

Đính kèm: 1 thành phần "Văn bản đề nghị cung cấp thông tin về quy hoạch..." (slotIndex 0) — gộp
Đơn đề nghị + Giấy chứng nhận + CCCD thành 1 PDF (FE applyMergeGroups theo sourceFileIndexes).
"""
