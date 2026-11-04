"""Pipeline "Tuyên Quang - Đăng ký đất đai, tài sản gắn liền với đất, cấp Giấy chứng nhận ... lần đầu" (1.013978).

Cổng iGate Tuyên Quang có BA quy trình (hộp thoại "Chọn trường hợp giải quyết"), mỗi quy trình một form bước 1:
``process`` (form "5 bước 20 ngày"), ``process_ilis`` (form "iLis cấp xã - 30 ngày") và ``process_vbdlis`` (form
"VBDLIS 20 ngày"). Ba form đọc CÙNG bộ facts (process/schema.FIELDS), chỉ khác cách xếp vào ô. Bảng đính kèm 20 dòng
của ba form giống nhau nên dùng chung ``attach``.
"""
