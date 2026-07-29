"""Pipeline "[Lâm Đồng] Đăng ký đất đai, tài sản gắn liền với đất, cấp GCN lần đầu
(hộ gia đình, cá nhân, cộng đồng dân cư, người gốc Việt Nam định cư ở nước ngoài)".

Cổng Lâm Đồng (Form.io apply-online) — CÙNG form/nền tảng với dinh_chinh_sai_sot_lam_dong: 4 khối
data[...] comp dom-*, nút copy data[BUTTON3]. KHÁC: Phần IV "Thông tin chi tiết" (GCN) là "không cần
điền" (đăng ký LẦN ĐẦU, chưa có GCN) → bỏ. Ghi chú để trống. Đính kèm GỘP nhiều file → 1 PDF/nhóm
(FE applyMergeGroups theo sourceFileIndexes), 4 nhóm cố định theo slotIndex.
"""
