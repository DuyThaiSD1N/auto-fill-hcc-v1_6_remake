# Handfree migration gate (bước 8.5)

Chạy trước khi chuyển dữ liệu hoặc cutover backend:

```bash
.venv/bin/python scripts/check_handfree_migration_gate.py
```

Gate chạy hai lớp:

1. Toàn bộ test Handfree còn phù hợp với core hợp nhất.
2. Các test canonical của Auto Fill cho auth, báo cáo, trace, OCR streaming, upload-session
   và process v2.

Danh sách `COLLECTION_DEBT` và `NODE_DEBT` trong script là nợ tương thích được đóng băng ở
đúng file/node; lỗi mới ngoài danh sách vẫn làm gate đỏ. Không được thêm test vào danh sách
này chỉ để làm CI xanh. Muốn xem lại toàn bộ nợ hiện tại:

```bash
.venv/bin/python scripts/check_handfree_migration_gate.py --audit-debt
```

Các nhóm nợ mapper/prompt/planner phải xử lý ở session thủ tục riêng theo AGENTS.md. Bộ
planner_v2 cũ không được dựng lại vì core hiện dùng contract attachment tích hợp.
