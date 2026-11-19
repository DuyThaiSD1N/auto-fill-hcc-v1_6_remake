"""Pipeline "Công nhận và giải quyết chế độ ưu đãi người hoạt động kháng chiến bị nhiễm chất độc hóa học" (1.010816).

Cổng Bộ Nội vụ (vào từ DVCQG), cùng họ Form.io với 1.010819 giải quyết chế độ người hoạt động kháng chiến. Mapping theo
Mapping_NHDKC_nhiem_CDHH_Mau09_BoNoiVu.xlsx: bước 1 có khối Người nộp (cổng khoá họ tên / ngày sinh / CCCD theo tài
khoản), khối Chủ hồ sơ (= người hoạt động kháng chiến, ô owner*), bảng "Hồ sơ kèm theo gồm" và eForm Bản khai Mẫu số 09
(Phụ lục I NĐ 131/2021/NĐ-CP) dùng lại key của khối Người nộp (data[fullname], data[province]…) → occurrence 1, có hai
datagrid quaTrinh / conDe. Bước 2 đính kèm attp-row 4 dòng, có chế độ tách giấy (attach/planner.py).

Tên package trùng key `cong-nhan-che-do-khang-chien-nhiem-chat-doc-hoa-hoc` của ke_khai_links.json.
"""
