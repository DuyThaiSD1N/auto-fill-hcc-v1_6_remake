# Chính sách quyền riêng tư — Trợ lý hồ sơ Dịch vụ công

**Cập nhật lần cuối:** 12/08/2026

Tiện ích mở rộng **"Trợ lý hồ sơ Dịch vụ công"** (sau đây gọi là "Tiện ích") hỗ trợ người dùng điền nhanh thông tin từ giấy tờ vào các biểu mẫu trên cổng Dịch vụ công. Chính sách này mô tả rõ Tiện ích thu thập dữ liệu gì, dùng để làm gì, lưu ở đâu và được bảo vệ ra sao.

> **Cam kết cốt lõi:** Chúng tôi **không bán, không cho thuê, không chia sẻ** dữ liệu của bạn cho bất kỳ bên thứ ba nào. Toàn bộ xử lý OCR và trích xuất thông tin diễn ra **trên máy chủ riêng của chúng tôi**, không gửi sang dịch vụ bên ngoài.

---

## 1. Dữ liệu chúng tôi thu thập

Tiện ích chỉ thu thập dữ liệu cần thiết để thực hiện đúng chức năng điền biểu mẫu:

| Loại dữ liệu | Nội dung | Khi nào |
|---|---|---|
| **Thông tin đăng nhập** | Tên đăng nhập và mật khẩu tài khoản do đơn vị cấp | Khi bạn đăng nhập vào Tiện ích |
| **Ảnh/tệp giấy tờ** | Hình ảnh hoặc PDF của giấy tờ bạn tải lên (ví dụ: căn cước công dân, giấy khai sinh, giấy chứng tử, giấy chứng nhận kết hôn…) | Khi bạn chọn tệp để xử lý |
| **Thông tin trích xuất** | Các trường thông tin đọc được từ giấy tờ (họ tên, số định danh, ngày sinh, địa chỉ…) | Sau khi máy chủ xử lý ảnh |
| **Nhật ký xử lý** | Thủ tục đã chọn, tên tệp, thời điểm, kết quả trích xuất, tài khoản thực hiện | Mỗi lần xử lý một hồ sơ |

Tiện ích **không** thu thập lịch sử duyệt web, không theo dõi hoạt động của bạn trên các trang khác, không đọc dữ liệu ngoài phạm vi các trang Dịch vụ công đã khai báo.

---

## 2. Mục đích sử dụng

Dữ liệu thu thập **chỉ** được dùng để:

- Xác thực đăng nhập và duy trì phiên làm việc của bạn.
- Đọc (OCR) và trích xuất thông tin từ giấy tờ để **tự động điền** vào biểu mẫu Dịch vụ công.
- Ghi nhật ký phục vụ vận hành, thống kê nội bộ và hỗ trợ khắc phục sự cố.

Chúng tôi **không** dùng dữ liệu của bạn cho quảng cáo, không phân tích hành vi vì mục đích tiếp thị.

---

## 3. Dữ liệu được gửi đi đâu

- Ảnh giấy tờ và thông tin đăng nhập được gửi từ Tiện ích tới **máy chủ backend riêng của chúng tôi** để xử lý.
- **Toàn bộ OCR và trích xuất bằng AI chạy trên máy chủ của chúng tôi.** Chúng tôi **không** chuyển nội dung giấy tờ của bạn cho bất kỳ dịch vụ bên thứ ba nào (không dùng dịch vụ AI/đám mây bên ngoài).

---

## 4. Lưu trữ dữ liệu

**Trên trình duyệt của bạn:**
- Mã phiên đăng nhập (access/refresh token) để bạn không phải đăng nhập lại mỗi lần.
- Nếu bạn chủ động chọn **"Ghi nhớ đăng nhập"**, tên đăng nhập và mật khẩu được mã hóa bằng
  AES-GCM 256-bit rồi lưu trong IndexedDB riêng của Tiện ích trên thiết bị. Khóa mã hóa là
  `CryptoKey` không cho phép xuất dữ liệu khóa (`extractable=false`). Thông tin này không được lưu
  ở dạng rõ, không dùng `chrome.storage.sync` và không đồng bộ sang thiết bị khác.
- Dữ liệu phiên tạm thời theo từng tab (thủ tục đang chọn và tệp đang xử lý) để khôi phục khi bạn mở lại. Dữ liệu này bị xóa khi bạn bắt đầu phiên mới hoặc đăng xuất.

**Trên máy chủ:**
- Kết quả trích xuất và nhật ký xử lý được lưu để phục vụ vận hành và thống kê.

Bạn có thể xóa thông tin đăng nhập được ghi nhớ bằng cách bỏ chọn **"Ghi nhớ đăng nhập"**, bấm
**"Xóa đã nhớ"**, hoặc gỡ Tiện ích. Nút **Đăng xuất** kết thúc phiên làm việc nhưng vẫn giữ thông
tin đã nhớ nếu bạn chưa yêu cầu xóa, để có thể tự điền ở lần đăng nhập sau.

---

## 5. Bảo mật

- Mật khẩu chỉ được lưu cục bộ khi người dùng chủ động bật **"Ghi nhớ đăng nhập"**; khi đó mật khẩu
  được mã hóa bằng AES-GCM và đặt trong kho IndexedDB thuộc origin riêng của Tiện ích. Website Dịch
  vụ công và content script không dùng chung kho này.
- Tính năng ghi nhớ đăng nhập bị vô hiệu hóa trong cửa sổ ẩn danh.
- Phiên đăng nhập dùng cơ chế token có thời hạn và có thể thu hồi.
- Chúng tôi áp dụng các biện pháp kỹ thuật hợp lý để bảo vệ dữ liệu trên máy chủ.

---

## 6. Quyền của bạn

Bạn có quyền:
- Yêu cầu biết dữ liệu nào của bạn đang được lưu.
- Yêu cầu xóa dữ liệu trích xuất/nhật ký liên quan đến tài khoản của bạn.
- Ngừng sử dụng và gỡ Tiện ích bất cứ lúc nào.

Để thực hiện các quyền trên, liên hệ theo thông tin ở Mục 9.

---

## 7. Đối tượng sử dụng

Tiện ích dành cho **cán bộ/người dùng được cấp tài khoản** để xử lý hồ sơ hành chính công. Không dành cho trẻ em và không chủ đích thu thập dữ liệu của trẻ em.

---

## 8. Thay đổi chính sách

Chính sách này có thể được cập nhật. Khi có thay đổi quan trọng, chúng tôi sẽ cập nhật ngày ở đầu tài liệu và (nếu cần) thông báo trong Tiện ích.

---

## 9. Liên hệ

- **Đơn vị phát triển:** _[Điền tên đơn vị/nhà phát triển]_
- **Email liên hệ:** _[Điền email hỗ trợ]_

---

---

# Phụ lục — Giải trình quyền (dùng khi khai báo trên Chrome Web Store)

Dán các đoạn dưới đây vào ô **"Permission justification"** tương ứng trong Developer Dashboard.

**`storage`**
Lưu mã phiên đăng nhập và dữ liệu phiên tạm thời (thủ tục + tệp đang xử lý) nhằm khôi phục khi người dùng mở lại tiện ích. Mật khẩu không được lưu trong `chrome.storage`; khi người dùng chủ động bật ghi nhớ, dữ liệu xác thực được mã hóa và lưu trong IndexedDB riêng của Tiện ích trên thiết bị.

**`unlimitedStorage`**
Dữ liệu phiên tạm thời có thể chứa ảnh/PDF giấy tờ (mã hóa base64) nhiều trang, dễ vượt hạn mức lưu trữ mặc định (~10MB). Quyền này bảo đảm việc lưu tạm và khôi phục tệp không bị lỗi vượt hạn mức. Dữ liệu bị xóa khi người dùng bắt đầu phiên mới hoặc đăng xuất.

**`activeTab`**
Cho phép tiêm tập lệnh điền biểu mẫu vào **tab Dịch vụ công đang mở** tại thời điểm người dùng chủ động bấm nút trong tiện ích. Chỉ tác động lên tab người dùng đang thao tác.

**`scripting`**
Cần để tiêm tập lệnh đọc cấu trúc biểu mẫu và điền dữ liệu đã trích xuất vào đúng ô trên trang Dịch vụ công.

**`host_permissions` (máy chủ backend)**
Tiện ích gọi API tới máy chủ riêng để xác thực và xử lý OCR/trích xuất. Đây là điểm đến duy nhất mà dữ liệu được gửi tới.

**`content_scripts` (các miền Dịch vụ công đã khai báo)**
Chỉ chạy trên các cổng Dịch vụ công cụ thể (moj.gov.vn, moh.gov.vn, dkkd.gov.vn, dichvucong.gov.vn, laichau.gov.vn…) để đọc và điền biểu mẫu. Không chạy trên các trang khác.

**`all_frames: true` (giữ sẵn để trả lời nếu reviewer hỏi — không có ô khai riêng)**
Nhiều biểu mẫu trên cổng Dịch vụ công được nhúng bên trong khung con (iframe). Tập lệnh phải hiện diện trong đúng khung chứa các ô nhập thì mới đọc và điền được dữ liệu. Vì vậy tập lệnh được tiêm vào mọi khung của các miền đã khai báo; nó chỉ đọc/điền biểu mẫu, không thu thập thêm dữ liệu nào khác.

**`run_at: "document_start"` (giữ sẵn để trả lời nếu reviewer hỏi)**
Tập lệnh cần khởi tạo sớm để bắt kịp các biểu mẫu được dựng động, tránh bỏ sót ô nhập xuất hiện trong quá trình trang tải. Không can thiệp vào hoạt động khác của trang.

**`web_accessible_resources` (popup.*, api/*)**
Giao diện trợ lý được hiển thị dưới dạng khung nhúng (iframe) ngay trên trang Dịch vụ công; khung này cần tải các tệp giao diện và tập lệnh gọi API của tiện ích. Các tệp này chỉ chứa mã giao diện và địa chỉ máy chủ, không chứa khóa bí mật hay dữ liệu người dùng.

**Tuyên bố sử dụng dữ liệu (Data usage)**
- Có thu thập: *Thông tin nhận dạng cá nhân* (nội dung giấy tờ) và *Thông tin xác thực* (đăng nhập).
- Không bán/chuyển nhượng dữ liệu cho bên thứ ba.
- Không dùng/chuyển dữ liệu cho mục đích không liên quan đến chức năng chính.
- Không dùng/chuyển dữ liệu để đánh giá khả năng tín dụng hoặc cho vay.
