// Lịch sử cập nhật extension — SỬA TAY khi phát hành bản mới:
//   thêm 1 mục lên ĐẦU mảng, đổi "version" cho khớp manifest.json (version mới nhất = đang dùng).
// Chỉ dữ liệu, không logic. Được nạp trước popup.js (biến toàn cục APP_RELEASES).
const APP_RELEASES = [
  {
    version: "1.18.5",
    date: "14/9/2026",
    items: [
      "Sửa lỗi đính kèm giấy tờ vào hồ sơ.",
    ],
  },
  {
    version: "1.18.4",
    date: "14/9/2026",
    items: [
      "Mở được thủ tục Đăng ký mua, thuê mua, thuê nhà ở xã hội (Bắc Ninh) từ ô Đi đến thủ tục: trợ lý đi qua cổng dịch vụ công quốc gia rồi tự chuyển sang đúng thủ tục trên cổng Bắc Ninh.",
    ],
  },
  {
    version: "1.18.3",
    date: "14/9/2026",
    items: [
      "Chỉ cần chọn Tỉnh/Thành phố là trợ lý tìm được cơ quan thực hiện; Phường/Xã không còn bắt buộc.",
      "Thẻ đánh giá sau khi gửi hồ sơ dễ đọc hơn khi rê chuột và khi đã chọn lý do.",
    ],
  },
  {
    version: "1.18.2",
    date: "14/9/2026",
    items: [
      "Sửa lỗi sau khi trợ lý tự cập nhật, bấm biểu tượng mở lại bảng thì các lần điền hồ sơ báo lỗi.",
    ],
  },
  {
    version: "1.18.1",
    date: "14/9/2026",
    items: [
      "Báo phiên bản đang chạy cho máy quét tại quầy để quản trị thấy từng máy dùng bản nào.",
    ],
  },
  {
    version: "1.18",
    date: "12/9/2026",
    items: [
      "Trợ lý đổi tên thành “Trợ lý nhân dân”.",
      "Thêm bước đánh giá trải nghiệm sau khi bấm Gửi hồ sơ; không bắt buộc.",
      "Ghi nhận thời điểm nộp hồ sơ: báo cáo hiện giờ nộp, số lần nộp và thời gian làm.",
      "Đính kèm: một tài liệu lỗi không còn chặn các tài liệu còn lại.",
      "Đính kèm chỉ báo thành công khi cổng thật sự ghi nhận; cổng lỗi thì hiện rõ lý do.",
      "Sửa lỗi một số ảnh chụp từ điện thoại không gộp được vào PDF.",
      "Khắc phục trường hợp điện thoại báo đã gửi ảnh nhưng máy tính không nhận được.",
      "Chứng thực chữ ký người dịch: tự đánh số thành phần hồ sơ trùng tên.",
      "Hỗ trợ thêm cổng Một cửa Bộ Nội vụ và cổng dịch vụ công Quảng Ninh.",
    ],
  },
  {
    version: "1.17",
    date: "8/9/2026",
    items: [
      "Thêm nút Xem báo cáo ở góc dưới trợ lý: mở thẳng bảng thống kê của đơn vị, tự đăng nhập bằng tài khoản đang dùng.",
    ],
  },
  {
    version: "1.16",
    date: "7/9/2026",
    items: [
      "Sửa lỗi ảnh giấy tờ chụp từ điện thoại qua mã QR không hiện lên máy tính; nay ảnh về đầy đủ.",
      "Nhận diện thủ tục: khi chuyển sang trang hoặc thủ tục chưa hỗ trợ nhận diện, tự bỏ chọn thủ tục cũ thay vì kẹt ở thủ tục trước.",
      "Đăng ký doanh nghiệp: hoàn thiện luồng điền cho thủ tục thành lập doanh nghiệp trên cổng đăng ký kinh doanh.",
      "Tự điền mô tả ngành nghề kinh doanh khi tờ khai chưa ghi mã ngành.",
      "Bắc Ninh: điền biểu mẫu ổn định hơn và tự điền nơi cấp giấy tờ tùy thân.",
      "Đi đến thủ tục và Chọn cơ quan thực hiện: chọn Tỉnh và Phường/Xã chính xác, ổn định hơn.",
    ],
  },
  {
    version: "1.15",
    date: "1/9/2026",
    items: [
      "Cập nhật kết nối máy chủ mới, giúp trợ lý hoạt động ổn định và liên tục.",
      "Hỗ trợ thêm nhiều thủ tục đất đai của thành phố Đà Nẵng: giao đất/cho thuê đất, chuyển mục đích sử dụng đất, tách/hợp thửa đất.",
      "Hỗ trợ thủ tục đăng ký đất đai và cấp Giấy chứng nhận quyền sử dụng đất lần đầu.",
      "Hỗ trợ thủ tục cấp đổi Giấy chứng nhận và xóa đăng ký biện pháp bảo đảm bằng quyền sử dụng đất.",
      "Nhận diện thủ tục chính xác và ổn định hơn theo tên hiển thị trên cổng dịch vụ công (ít bị nhận nhầm hơn).",
    ],
  },
  {
    version: "1.14",
    date: "23/8/2026",
    items: [
      "Thêm mục Đi đến thủ tục: mở đúng trang kê khai trên Cổng Dịch vụ công quốc gia, tự chọn Tỉnh và Phường/Xã ở bước Chọn cơ quan thực hiện, rồi bấm Nộp trực tuyến và xác nhận thông tin chung giúp cán bộ.",
      "Chọn nhanh tỉnh và phường/xã theo danh mục hành chính mới sau sáp nhập ngay trên trợ lý.",
      "Điền chính xác và đúng thứ tự thông tin Người nộp hồ sơ và Chủ hồ sơ ở các thủ tục có hai vai trò.",
      "Đăng ký hộ kinh doanh: hoàn thiện luồng điền cho thủ tục Thay đổi nội dung đăng ký và Chấm dứt hoạt động.",
      "Hỗ trợ đính kèm cho thủ tục Chứng thực bản sao từ bản chính và Chứng thực chữ ký người dịch là cộng tác viên: mỗi tài liệu được tách thành một hồ sơ riêng, xử lý tuần tự trên từng tab kèm hiển thị tiến độ.",
      "Ảnh giấy tờ khi đính kèm được chuyển sang PDF giữ nguyên chất lượng (không nén lại); gộp và tách nhiều tài liệu chính xác hơn.",
      "Cải thiện độ ổn định khi điền trên biểu mẫu eForm cũ và nhóm thủ tục chứng thực (tách/gộp hồ sơ).",
    ],
  },
  {
    version: "1.13",
    date: "16/8/2026",
    items: [
      "Giữ nguyên giấy tờ đã chọn khi tải lại hoặc chuyển bước trong cùng thủ tục; tự xóa giấy tờ cũ khi chuyển sang thủ tục khác để tránh dùng nhầm hồ sơ.",
      "Tự nhận diện lại thủ tục khi cổng dịch vụ công chuyển trang không tải lại; cho phép người dùng bấm chọn thủ tục khác nếu kết quả nhận diện chưa chính xác.",
      "Sau khi máy chủ trả dữ liệu, Trợ lý tự thu nhỏ trước khi điền để cán bộ dễ quan sát biểu mẫu; tự mở lại nếu không điền được hoặc khi đến bước đính kèm.",
      "Rút gọn thông báo kết quả điền, bổ sung nút Xem chi tiết khi có trường chưa khớp và không hiển thị lỗi kỹ thuật thô.",
      "Hiển thị thông báo hoàn tất ngay trên trang sau khi điền hoặc đính kèm hồ sơ; cải thiện màu hover, focus và khả năng đọc của ô chọn thủ tục.",
      "Giảm dung lượng gửi hồ sơ lên máy chủ bằng multipart binary; dùng chung một API cho quét điền và phân tích đính kèm.",
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
