"""Thông báo bảo vệ dữ liệu cá nhân hiện một lần đầu mỗi lượt công dân (trước khi mở phiên), chỉ có nút xác nhận đã đọc.

Extension lấy qua GET /api/v1/voice/config (khoá "privacyNotice") → sửa chữ ở đây, không phải phát hành extension.
Đổi nội dung thì nâng "version": extension lưu phiên bản đã xác nhận, thấy phiên bản mới là hiện lại.
Không thay quy trình xin đồng ý xử lý dữ liệu (thẻ consent trong luồng thủ tục vẫn như cũ).
"""

NOTICE: dict = {
    "version": "1.0",
    "title": "Bảo vệ dữ liệu cá nhân khi dùng trợ lý",
    "summary": [
        "Trợ lý đọc ảnh giấy tờ công dân tải lên và tự điền sẵn vào tờ khai. Việc này do máy làm tự động.",
        "Máy có thể đọc hoặc điền sai. Công dân cần kiểm tra và sửa trước khi nộp.",
        "Trợ lý không quyết định kết quả. Cơ quan có thẩm quyền giải quyết hồ sơ.",
        "Hết phiên nộp hồ sơ, dữ liệu tự xóa, trợ lý không lưu lại.",
        "Công dân có quyền không dùng trợ lý. Không dùng, công dân vẫn nộp hồ sơ bình thường.",
    ],
    "expand_label": "Xem đầy đủ 6 nội dung về bảo vệ dữ liệu cá nhân",
    "collapse_label": "Thu gọn nội dung đầy đủ",
    "detail_title": "Thông báo quan trọng!",
    "detail_intro": (
        "Công dân vui lòng đọc kỹ thông báo dưới đây về Bảo vệ dữ liệu cá nhân trong hệ thống trí tuệ nhân tạo "
        "trước khi lựa chọn sử dụng Trợ lý nhân dân."
    ),
    # heading: phần in đậm đầu mục (có thể rỗng) · text: đoạn tiếp theo · bullets: [[nhãn in đậm, nội dung], …]
    "items": [
        {
            "heading": "Cách thức Trợ lý nhân dân xử lý dữ liệu cá nhân:",
            "text": "Dữ liệu cá nhân của Công dân được xử lý trên hệ thống một cách tự động.",
        },
        {
            "heading": "Nguyên tắc hoạt động của thuật toán như sau:",
            "text": (
                "Trợ lý dùng công nghệ nhận dạng chữ (OCR) để đọc giấy tờ Công dân cung cấp. Sau đó mô hình trí tuệ "
                "nhân tạo trích ra những thông tin biểu mẫu của thủ tục cần và tự điền sẵn vào biểu mẫu trên Cổng Dịch "
                "vụ công. Trợ lý chỉ điền sẵn, không quyết định kết quả hồ sơ. Cán bộ và người dân kiểm tra, sửa trước "
                "khi nộp; việc giải quyết hồ sơ do cơ quan có thẩm quyền thực hiện."
            ),
        },
        {
            "heading": "Ảnh hưởng đối với quyền và lợi ích hợp pháp của Công dân (chủ thể dữ liệu):",
            "bullets": [
                [
                    "Ảnh hưởng tích cực:",
                    "Ứng dụng Trợ lý nhân dân giúp tự động hóa việc tra cứu thông tin, điền biểu mẫu, phân loại hồ sơ, "
                    "từ đó rút ngắn đáng kể thời gian giải quyết thủ tục hành chính cho Công dân.",
                ],
                [
                    "Ảnh hưởng tiêu cực:",
                    "Dữ liệu đầu vào có thể bị sai lệch do lỗi đọc, điền thông tin, lỗi thuật toán hoặc hiện tượng "
                    "\"ảo giác\" của hệ thống trí tuệ nhân tạo được ứng dụng trong Trợ lý nhân dân. Điều này có thể dẫn "
                    "đến việc điền sai, đánh giá sai hồ sơ của Công dân. Do đó, Công dân cần đọc, kiểm tra kỹ lại toàn "
                    "bộ hồ sơ trước khi nộp cho cơ quan nhà nước.",
                ],
            ],
        },
        {
            "heading": "Công dân có quyền chọn dùng hoặc không dùng ứng dụng AI Trợ lý nhân dân:",
            "text": (
                "Trong trường hợp Công dân không đồng ý với các thông tin và cách thức xử lý dữ liệu cá nhân trên đây, "
                "Công dân có thể bỏ qua và không sử dụng Trợ lý nhân dân để hỗ trợ chọn thủ tục, đọc giấy tờ, điền "
                "biểu mẫu và đính kèm hồ sơ."
            ),
        },
        {
            "heading": "",
            "text": (
                "Sau khi kết thúc phiên nộp hồ sơ, ứng dụng AI Trợ lý nhân dân không lưu trữ bất cứ thông tin/dữ liệu "
                "nào của Công dân (kể cả lịch sử sử dụng ứng dụng hay lịch sử hành vi). Điều này có nghĩa là mọi thông "
                "tin/dữ liệu cá nhân của Công dân được xử lý hệ thống ứng dụng Trợ lý nhân dân sẽ được tự động xóa "
                "hoàn toàn ngay khi kết thúc phiên nộp hồ sơ."
            ),
        },
        {
            "heading": "Thu thập dữ liệu trên trình duyệt:",
            "text": (
                "Khi cán bộ/người dân dùng Trợ lý trên trang Cổng Dịch vụ công đang mở, Trợ lý đọc cấu trúc biểu mẫu "
                "của trang đó — tên ô, nhãn, loại ô (ô chữ, ô ngày, danh sách chọn), các lựa chọn có sẵn và vị trí của "
                "từng ô — để xác định thông tin trích từ giấy tờ cần điền vào ô nào. Trợ lý chỉ đọc trang của thủ tục "
                "đang thực hiện, không đọc các trang hay thẻ trình duyệt khác."
            ),
        },
    ],
    "version_line": "Thông báo bảo vệ dữ liệu cá nhân, phiên bản 1.0, ngày 12/11/2026",
    "ok_label": "Tôi đã hiểu",
}
