"""Pipeline thủ tục giao đất, cho thuê đất, chuyển mục đích sử dụng đất, giao rừng, gia hạn (1.013949) — iGate Tuyên Quang.

Hai form theo quy trình người dân chọn: ``process`` (form 1, quy trình thường) và ``process_vbdlis`` (form 2, quy trình
"VBDLIS"). Hai form đọc CÙNG bộ facts (process/schema.FIELDS), chỉ khác cách xếp vào ô. Bảng đính kèm 14 dòng của hai
form giống nhau nên dùng chung ``attach``.
"""
