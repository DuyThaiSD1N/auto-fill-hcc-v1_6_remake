// Lịch sử cập nhật extension — SỬA TAY khi phát hành bản mới:
//   thêm 1 mục lên ĐẦU mảng, đổi "version" cho khớp manifest.json (version mới nhất = đang dùng).
// Chỉ dữ liệu, không logic. Được nạp trước popup.js (biến toàn cục APP_RELEASES).
const APP_RELEASES = [
  {
    version: "1.13",
    date: "16/8/2026",
    items: [
      "Giữ nguyên giấy tờ đã chọn khi tải lại hoặc chuyển bước trong cùng thủ tục; tự xóa giấy tờ cũ khi chuyển sang thủ tục khác để tránh dùng nhầm hồ sơ.",
      "Tự nhận diện lại thủ tục khi cổng dịch vụ công chuyển trang không tải lại; cho phép người dùng bấm chọn thủ tục khác nếu kết quả nhận diện chưa chính xác.",
      "Sau khi máy chủ trả dữ liệu, Trợ lý tự thu nhỏ trước khi điền để cán bộ dễ quan sát biểu mẫu; tự mở lại nếu không điền được hoặc khi đến bước đính kèm.",
      "Rút gọn thông báo kết quả điền, bổ sung nút Xem chi tiết khi có trường chưa khớp và không hiển thị lỗi kỹ thuật thô.",
      "Hiển thị thông báo hoàn tất ngay trên trang sau khi điền hoặc đính kèm hồ sơ; cải thiện màu hover, focus và khả năng đọc của ô chọn thủ tục.",
    ],
  },
  {
    version: "1.12",
    date: "13/8/2026",
    items: [
      "Chỉnh sửa để phù hợp với trình duyệt firefox",
      "Sửa một số lỗi về đăng ký hộ kinh doanh",
      "Bổ sung tùy chọn ghi nhớ đăng nhập: tự điền tài khoản và mật khẩu ở lần đăng nhập sau khi người dùng chủ động bật tính năng.",
      "Nhận ổn định các tệp PDF dung lượng lớn tải từ điện thoại về máy tính.",
      "Điền chính xác hơn phường/xã sau sáp nhập trên biểu mẫu (khắc phục trường hợp chọn nhầm đơn vị có tên gần giống).",
      "Tối ưu thêm về phần chứng thực tránh trường hợp các file quá lớn"
    ],
  },
  {
    version: "1.11",
    date: "9/8/2026",
    items: [
      "Cải tiến luồng đính kèm nhiều tab cho nhóm thủ tục chứng thực: mỗi bộ tài liệu được xử lý tuần tự trên từng tab, hạn chế nhầm lẫn và sai sót.",
      "Khắc phục lỗi không đính kèm được tệp Word (.docx).",
      "Thông báo lỗi rõ ràng, dễ hiểu hơn khi gặp sự cố: đính kèm sai định dạng tệp, hoặc tệp/tổng dung lượng vượt quá giới hạn cho phép.",
    ],
  },
  {
    version: "1.10",
    date: "6/8/2026",
    items: [
      "Bổ sung bước xác nhận đồng ý xử lý dữ liệu cá nhân trước khi tự động điền: hiển thị đầy đủ điều khoản, quyền và nghĩa vụ của chủ thể dữ liệu theo quy định về bảo vệ dữ liệu cá nhân.",
      "Tải tài liệu bằng điện thoại qua mã QR nay hỗ trợ thêm tệp PDF, không chỉ ảnh.",
      "Khắc phục một số lỗi khi đính kèm hồ sơ ở nhóm thủ tục chứng thực.",
      "Khắc phục một số lỗi nhận diện và điền ở nhóm thủ tục đất đai.",
    ],
  },
  {
    version: "1.9",
    date: "4/8/2026",
    items: [
      "Thêm tính năng tải ảnh giấy tờ bằng điện thoại qua mã QR: quét mã, chụp hoặc chọn ảnh trên điện thoại, ảnh tự về extension.",
    ],
  },
  {
    version: "1.8",
    date: "3/8/2026",
    items: [
      "Đăng ký hộ kinh doanh: hỗ trợ thêm thủ tục Thay đổi nội dung đăng ký và Chấm dứt hoạt động hộ kinh doanh.",
      "Hỗ trợ cổng dịch vụ công Bộ Nông nghiệp và Môi trường: điền và đính kèm hồ sơ.",
      "Hỗ trợ đính kèm hồ sơ cho thủ tục cấp Giấy chứng nhận an toàn thực phẩm.",
      "Đọc chính xác hơn số điện thoại và email trên giấy tờ.",
    ],
  },
  {
    version: "1.7",
    date: "30/7/2026",
    items: [
      "Thêm lịch sử cập nhật & nội dung thay đổi theo từng phiên bản.",
      "Đăng ký hộ kinh doanh: bổ sung mô tả ngành nghề chi tiết nếu có",
      "Đăng ký hộ kinh doanh: điền các thông tin đầy đủ hơn như: số lao động, phương pháp tính thuế",
      "Cải thiện việc điền các thông tin về tỉnh và phường/xã",
      "Cải thiện tốc độ quét và xử lý hồ sơ.",
    ],
  },
  {
    version: "1.6",
    date: "26/7/2026",
    items: [
      "Bổ sung nhận diện và điền nhanh thông tin hồ sơ.",
      "Cải thiện độ chính xác khi đọc giấy tờ viết tay.",
      "Tối ưu tốc độ quét và nhập dữ liệu lên biểu mẫu.",
    ],
  }
];
