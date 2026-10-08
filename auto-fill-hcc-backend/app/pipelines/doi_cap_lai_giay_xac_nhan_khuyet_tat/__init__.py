"""Pipeline cho thủ tục "Đổi, cấp lại Giấy xác nhận khuyết tật" (mã TTHC 1.001653, cổng Bộ Y tế).

Tên package trùng key `doi-cap-lai-giay-xac-nhan-khuyet-tat` của ke_khai_links.json để tra.

Form kê khai là CÙNG eForm Mẫu số 01 với thủ tục 1.001699 (pipelines/khuyet_tat): người nộp, chủ hồ sơ,
người khuyết tật, người đại diện, bảng dạng khuyết tật và mức độ hoạt động trùng field-key. Chỉ khác:
- ``data[chonNoiDungDeNghi][]`` còn hai ô: 3 = Cấp lại, 4 = Cấp đổi;
- thêm ô bắt buộc ``data[LydoCapdoiCaplaiMa]`` (Lý do cấp đổi, cấp lại);
- bước Thành phần hồ sơ chỉ có MỘT dòng: Đơn đề nghị cấp đổi, cấp lại theo Mẫu số 01.
Vì vậy pipeline này dùng lại mapper/vision/context của khuyet_tat, chỉ ghi đè phần khác.
"""
