"""Bổ sung ô còn trống trên Đơn đăng ký hoạt động Trung tâm tư vấn pháp luật sau khi điền (chat/field_review)."""

PROCEDURE_KEYS = ("dang-ky-hoat-dong-trung-tam-tu-van-phap-luat",)

# Ô bắt buộc theo Mẫu TP-TVPL-01-sđ: Kính gửi, tên + quyết định thành lập + tổ chức chủ quản, tên đầy đủ, trụ sở,
# điện thoại, nhân thân + giấy tờ tùy thân Giám đốc, phạm vi hoạt động, dòng 1 danh sách nhân sự (Giám đốc), nơi ký và
# người ký. Tên viết tắt, fax, email, thẻ tư vấn viên / chứng chỉ / thẻ luật sư (tùy Giám đốc là tư vấn viên hay luật
# sư) và dòng 2–3 danh sách không bắt buộc. Ô cổng chấm đỏ khi bấm Xem trước vẫn được extension gộp thêm vào danh sách.
REQUIRED = (
    "KinhGui", "TTTVPL", "Quyetdinhso", "Ngay2", "TTTVPL2",
    "Tendaydu", "DCTS_Tinh", "DCTS_Xa", "Diachitruso", "DienthoaiC",
    "Hovaten", "Gioitinh", "Ngaythangnam", "Quoctich",
    "LoaiGiayToDinhDanhC", "Sothe", "Ngaythangnam1", "Noicap",
    "Phamvihoatdong", "Hovaten1", "Chucdanh",
    "TinhThanhPho", "Chuky",
)
