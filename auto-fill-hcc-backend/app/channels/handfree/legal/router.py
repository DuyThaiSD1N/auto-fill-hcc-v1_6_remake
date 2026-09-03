"""Chính sách quyền riêng tư công khai — GET /privacy.

Chrome Web Store BẮT BUỘC một URL chính sách công khai (không đăng nhập) khi tiện ích thu thập
dữ liệu cá nhân/nhạy cảm (ở đây: ảnh giấy tờ = PII, tài khoản đăng nhập, giọng nói/chat).
Nội dung phải KHỚP phần khai "Data usage" trên store VÀ khớp hành vi thật của hệ thống.

QUAN TRỌNG — trạng thái đích: chính sách này cam kết "không lưu ảnh/PDF/nội dung trích xuất" và
"không gửi sang dịch vụ bên thứ ba". Code phải được chỉnh cho ĐÚNG cam kết này TRƯỚC khi công bố
(hiện storage/files.py có lưu file + traces; OCR có provider bên thứ ba) — nếu không sẽ là khai sai.

Thông tin đơn vị/liên hệ lấy từ settings (đổi qua .env). Dùng token __ORG__/__EMAIL__/... thay
f-string để tránh đụng dấu ngoặc nhọn trong CSS.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import settings

router = APIRouter(tags=["legal"])

_PRIVACY_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<meta name="robots" content="index, follow" />
<title>Chính sách quyền riêng tư — Trợ lý người dân</title>
<style>
  :root {
    --bg: #f4f6f9; --card: #ffffff; --ink: #1f2933; --muted: #52606d;
    --line: #e4e7eb; --accent: #0f766e; --accent-soft: #e6f4f1;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0f1720; --card: #16202b; --ink: #e6edf3; --muted: #9aa7b4;
      --line: #263241; --accent: #5eead4; --accent-soft: #14312c;
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font: 16px/1.65 -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
  }
  .wrap { max-width: 780px; margin: 0 auto; padding: 32px 20px 64px; }
  header.doc {
    background: var(--accent-soft); border: 1px solid var(--line);
    border-radius: 16px; padding: 24px 26px; margin-bottom: 26px;
  }
  header.doc .kicker {
    text-transform: uppercase; letter-spacing: .08em; font-size: 12.5px;
    font-weight: 700; color: var(--accent); margin: 0 0 6px;
  }
  header.doc h1 { margin: 0 0 8px; font-size: 26px; line-height: 1.25; }
  header.doc .meta { margin: 0; color: var(--muted); font-size: 14px; }
  main {
    background: var(--card); border: 1px solid var(--line);
    border-radius: 16px; padding: 8px 28px 28px;
  }
  h2 {
    font-size: 18px; margin: 30px 0 10px; padding-top: 18px;
    border-top: 1px solid var(--line);
  }
  h2:first-of-type { border-top: 0; padding-top: 8px; }
  h3 { font-size: 15.5px; margin: 18px 0 4px; }
  p { margin: 10px 0; }
  ul { margin: 10px 0; padding-left: 22px; }
  li { margin: 6px 0; }
  a { color: var(--accent); }
  .lead { color: var(--muted); }
  code {
    background: var(--accent-soft); border: 1px solid var(--line);
    border-radius: 6px; padding: 1px 6px; font-size: 14px;
  }
  .callout {
    background: var(--accent-soft); border: 1px solid var(--line);
    border-radius: 12px; padding: 14px 18px; margin: 16px 0;
  }
  footer { margin-top: 26px; color: var(--muted); font-size: 13.5px; text-align: center; }
</style>
</head>
<body>
  <div class="wrap">
    <header class="doc">
      <p class="kicker">Chính sách quyền riêng tư</p>
      <h1>Tiện ích &ldquo;Trợ lý người dân&rdquo;</h1>
      <p class="meta">Đơn vị phát triển: __ORG__ &middot; Cập nhật lần cuối: __UPDATED__</p>
    </header>

    <main>
      <p class="lead">
        Chính sách này áp dụng cho tiện ích mở rộng &ldquo;Trợ lý người dân&rdquo; (sau đây gọi là
        &ldquo;Tiện ích&rdquo;) — công cụ hỗ trợ cán bộ hoặc người dùng được cấp tài khoản trích xuất
        thông tin từ giấy tờ hành chính, tự động điền vào biểu mẫu và được trợ lý hỏi–đáp bằng giọng nói
        và chat trên các cổng Dịch vụ công. Chúng tôi chỉ thu thập, sử dụng, lưu trữ dữ liệu trong phạm
        vi cần thiết để cung cấp chức năng chính; không bán, không cho thuê, không chia sẻ dữ liệu người
        dùng cho bên thứ ba vì mục đích quảng cáo, tiếp thị, môi giới dữ liệu hoặc mục đích thương mại
        không liên quan.
      </p>

      <h2>1. Đơn vị phát triển và liên hệ</h2>
      <ul>
        <li>Đơn vị phát triển: <strong>__ORG__</strong></li>
        <li>Email hỗ trợ: <a href="mailto:__EMAIL__">__EMAIL__</a></li>
        __PHONE_ROW__
      </ul>
      <p>Khi có câu hỏi, yêu cầu hỗ trợ hoặc yêu cầu liên quan đến dữ liệu cá nhân, người dùng vui lòng
        liên hệ qua email nêu trên.</p>

      <h2>2. Mục đích chính của Tiện ích</h2>
      <p>Tiện ích có một mục đích chính là hỗ trợ người dùng xử lý hồ sơ hành chính công bằng cách:</p>
      <ul>
        <li>Tiếp nhận ảnh hoặc tệp PDF giấy tờ do người dùng chủ động tải lên.</li>
        <li>Gửi tệp tới máy chủ backend do chúng tôi quản lý để thực hiện OCR và trích xuất thông tin.</li>
        <li>Trả lại thông tin đã trích xuất để người dùng kiểm tra và điền nhanh vào biểu mẫu trên cổng
          Dịch vụ công.</li>
        <li>Cung cấp trợ lý hỏi–đáp bằng giọng nói và chat để hướng dẫn người dùng theo từng bước của
          thủ tục.</li>
        <li>Hỗ trợ khôi phục phiên làm việc tạm thời khi người dùng mở lại Tiện ích hoặc thao tác trên
          nhiều tab thuộc các cổng Dịch vụ công đã khai báo.</li>
      </ul>
      <p>Tiện ích không được thiết kế để theo dõi người dùng, không thu thập lịch sử duyệt web và không
        hoạt động trên các trang web ngoài phạm vi đã khai báo phục vụ chức năng điền biểu mẫu Dịch vụ
        công.</p>

      <h2>3. Dữ liệu chúng tôi thu thập</h2>
      <h3>Thông tin đăng nhập</h3>
      <p>Gồm tên đăng nhập và mật khẩu tài khoản do đơn vị cấp, được người dùng nhập khi đăng nhập.
        Mật khẩu chỉ được gửi tới máy chủ để xác thực và không được lưu trên trình duyệt.</p>
      <h3>Ảnh hoặc tệp giấy tờ</h3>
      <p>Gồm hình ảnh hoặc tệp PDF giấy tờ do người dùng chủ động chọn để xử lý (ví dụ: căn cước công
        dân, giấy khai sinh, giấy chứng tử, giấy chứng nhận kết hôn hoặc giấy tờ hành chính khác). Các
        tệp này chỉ được xử lý tức thời để trích xuất thông tin và <strong>không được máy chủ lưu trữ
        lại</strong> sau khi hoàn tất.</p>
      <h3>Thông tin được trích xuất từ giấy tờ</h3>
      <p>Gồm các trường đọc được từ ảnh/PDF (ví dụ: họ tên, số định danh, ngày sinh, giới tính, địa chỉ,
        ngày cấp, nơi cấp…). Thông tin này chỉ được trả về Tiện ích để người dùng kiểm tra và điền biểu
        mẫu; máy chủ <strong>không lưu trữ lại</strong> nội dung trích xuất.</p>
      <h3>Giọng nói và nội dung hội thoại</h3>
      <p>Khi người dùng bật tính năng nói, Tiện ích thu âm thanh từ micro để nhận dạng giọng nói và có
        thể phát lại giọng đọc; nội dung chat do người dùng nhập cũng được xử lý để vận hành trợ lý.
        Âm thanh và nội dung hội thoại chỉ được xử lý phục vụ chức năng trợ lý và không được lưu trữ lại
        sau khi hoàn tất phiên.</p>
      <h3>Dữ liệu phiên làm việc</h3>
      <p>Gồm thủ tục đang chọn, trạng thái xử lý, tệp đang xử lý và dữ liệu tạm theo từng tab nhằm hỗ trợ
        khôi phục thao tác. Dữ liệu này được lưu tạm trên trình duyệt của người dùng, không lưu trên máy
        chủ.</p>
      <h3>Nhật ký kỹ thuật tối thiểu</h3>
      <p>Gồm thời điểm gọi dịch vụ, trạng thái thành công/lỗi và thông tin kỹ thuật cần thiết để vận hành
        và khắc phục sự cố. Nhật ký này không chứa ảnh giấy tờ, tệp PDF hay nội dung cá nhân trích xuất
        từ giấy tờ.</p>

      <h2>4. Dữ liệu chúng tôi không thu thập</h2>
      <ul>
        <li>Không thu thập lịch sử duyệt web của người dùng.</li>
        <li>Không theo dõi hoạt động của người dùng trên các trang web không liên quan.</li>
        <li>Không đọc nội dung email, tin nhắn, mạng xã hội hoặc tài khoản cá nhân khác.</li>
        <li>Không thu thập dữ liệu vị trí chính xác (GPS) của người dùng.</li>
        <li>Không thu thập dữ liệu thanh toán, thẻ ngân hàng hoặc thông tin tài chính cá nhân.</li>
        <li>Không dùng dữ liệu để chấm điểm tín dụng, đánh giá khả năng vay, quảng cáo cá nhân hóa hoặc
          tiếp thị lại.</li>
      </ul>

      <h2>5. Cách chúng tôi sử dụng dữ liệu</h2>
      <ul>
        <li>Xác thực tài khoản và duy trì phiên đăng nhập của người dùng.</li>
        <li>Thực hiện OCR và trích xuất thông tin từ ảnh hoặc tệp PDF giấy tờ.</li>
        <li>Hiển thị thông tin đã trích xuất để người dùng kiểm tra trước khi điền biểu mẫu.</li>
        <li>Tự động điền thông tin vào các ô biểu mẫu trên cổng Dịch vụ công khi người dùng chủ động
          thực hiện thao tác.</li>
        <li>Nhận dạng giọng nói và phát giọng đọc để vận hành trợ lý hỏi–đáp theo yêu cầu của người dùng.</li>
        <li>Lưu tạm dữ liệu phiên trên trình duyệt nhằm hỗ trợ khôi phục thao tác.</li>
        <li>Ghi nhật ký kỹ thuật tối thiểu (không chứa nội dung giấy tờ) phục vụ vận hành, kiểm tra lỗi
          và hỗ trợ người dùng.</li>
        <li>Bảo vệ hệ thống, phát hiện lỗi kỹ thuật, ngăn chặn lạm dụng hoặc truy cập trái phép.</li>
      </ul>
      <p>Chúng tôi không sử dụng dữ liệu người dùng cho quảng cáo, không bán dữ liệu và không chuyển dữ
        liệu cho nền tảng quảng cáo, nhà môi giới dữ liệu hoặc bên thứ ba phục vụ mục đích tiếp thị.</p>

      <h2>6. Dữ liệu được gửi đi đâu</h2>
      <p>Khi người dùng đăng nhập, tải tệp giấy tờ hoặc dùng tính năng nói, dữ liệu được gửi từ Tiện ích
        tới máy chủ backend do chúng tôi quản lý. Toàn bộ quá trình OCR, nhận dạng giọng nói và trích
        xuất thông tin được xử lý trên hệ thống máy chủ do chúng tôi quản lý.</p>
      <p>Chúng tôi <strong>không gửi</strong> ảnh giấy tờ, tệp PDF, âm thanh hoặc nội dung trích xuất
        sang dịch vụ AI, OCR hay nền tảng đám mây của bên thứ ba để xử lý. Sau khi trả kết quả về Tiện
        ích, máy chủ không lưu lại ảnh, tệp PDF hay nội dung trích xuất.</p>
      <p>Dữ liệu không được chia sẻ cho bên thứ ba, trừ trường hợp bắt buộc theo quy định pháp luật, yêu
        cầu hợp lệ của cơ quan có thẩm quyền hoặc khi cần thiết để bảo vệ an toàn hệ thống và người dùng.</p>

      <h2>7. Lưu trữ dữ liệu trên trình duyệt</h2>
      <p>Tiện ích có thể dùng <code>chrome.storage.local</code> để lưu cục bộ trên trình duyệt:</p>
      <ul>
        <li>Access token và refresh token để duy trì phiên đăng nhập.</li>
        <li>Tên đăng nhập để tự điền sẵn ở lần đăng nhập sau.</li>
        <li>Dữ liệu phiên tạm thời như thủ tục đang chọn, trạng thái xử lý và tệp đang xử lý.</li>
      </ul>
      <p>Dữ liệu cục bộ chỉ phục vụ trải nghiệm sử dụng Tiện ích; mật khẩu không được lưu trên trình
        duyệt. Người dùng có thể xóa dữ liệu này bằng cách đăng xuất, xóa dữ liệu trình duyệt hoặc gỡ
        Tiện ích khỏi Chrome.</p>

      <h2>8. Lưu trữ dữ liệu trên máy chủ</h2>
      <p>Máy chủ xử lý ảnh, tệp PDF, âm thanh và nội dung trích xuất một cách tức thời trong bộ nhớ để
        phục vụ yêu cầu của người dùng và <strong>không lưu trữ lại</strong> các dữ liệu này sau khi hoàn
        tất.</p>
      <p>Máy chủ chỉ lưu những dữ liệu tối thiểu cần cho hoạt động đăng nhập: thông tin tài khoản được
        cấp và token phiên đăng nhập. Mật khẩu không được lưu ở dạng có thể đọc được. Máy chủ không lưu
        ảnh giấy tờ, tệp PDF hay thông tin cá nhân trích xuất từ giấy tờ. Nhật ký kỹ thuật (nếu có) chỉ
        chứa thông tin vận hành, không chứa nội dung giấy tờ.</p>

      <h2>9. Bảo mật dữ liệu</h2>
      <ul>
        <li>Không lưu mật khẩu trên trình duyệt.</li>
        <li>Sử dụng token có thời hạn để duy trì phiên đăng nhập và cho phép thu hồi phiên khi cần.</li>
        <li>Giới hạn quyền truy cập dữ liệu theo vai trò và mục đích công việc.</li>
        <li>Truyền dữ liệu giữa Tiện ích và máy chủ qua kết nối bảo mật (HTTPS/WSS).</li>
        <li>Áp dụng các biện pháp bảo vệ máy chủ nhằm giảm thiểu rủi ro truy cập trái phép, mất mát, thay
          đổi hoặc tiết lộ dữ liệu ngoài ý muốn.</li>
      </ul>
      <p>Dù áp dụng các biện pháp hợp lý, không hệ thống nào bảo đảm an toàn tuyệt đối. Khi phát hiện sự
        cố có thể ảnh hưởng đến dữ liệu người dùng, chúng tôi sẽ xử lý, khắc phục và thông báo theo quy
        định áp dụng.</p>

      <h2>10. Quyền truy cập của Tiện ích</h2>
      <p>Tiện ích chỉ yêu cầu các quyền cần thiết để thực hiện chức năng chính:</p>
      <ul>
        <li><strong>storage</strong>: lưu token đăng nhập, tên đăng nhập và dữ liệu phiên tạm thời
          (không lưu mật khẩu).</li>
        <li><strong>unlimitedStorage</strong>: lưu tạm ảnh/PDF giấy tờ dung lượng lớn trong phiên xử lý,
          tránh lỗi vượt giới hạn lưu trữ cục bộ mặc định.</li>
        <li><strong>activeTab</strong>: thao tác với tab Dịch vụ công đang mở khi người dùng chủ động
          bấm nút trong Tiện ích.</li>
        <li><strong>offscreen</strong>: thu âm thanh từ micro cho tính năng nhận dạng giọng nói và phát
          giọng đọc chạy nền, do micro/âm thanh bị chặn trong khung nhúng của trợ lý.</li>
        <li><strong>host permissions</strong> (máy chủ backend): gọi API xác thực, tải tệp và nhận kết
          quả OCR/trích xuất; mở kết nối WebSocket cho nhận dạng giọng nói.</li>
        <li><strong>content scripts</strong>: chỉ chạy trên các miền Dịch vụ công đã khai báo để đọc cấu
          trúc biểu mẫu và điền dữ liệu.</li>
        <li><strong>web accessible resources</strong>: hiển thị giao diện trợ lý dưới dạng khung nhúng và
          tải các tệp giao diện cần thiết; chỉ chứa mã giao diện/cấu hình, không chứa mật khẩu, khóa bí
          mật hay dữ liệu cá nhân.</li>
      </ul>
      <p>Tiện ích không dùng các quyền này để theo dõi người dùng trên website khác, thu thập lịch sử
        duyệt web hoặc đọc dữ liệu ngoài phạm vi chức năng đã công bố.</p>

      <h2>11. Tập lệnh nội dung và iframe</h2>
      <p>Một số biểu mẫu trên cổng Dịch vụ công được nhúng trong iframe hoặc dựng động khi tải trang. Vì
        vậy Tiện ích có thể cần chạy tập lệnh trong các khung phù hợp của các miền đã khai báo để nhận
        diện ô nhập và điền dữ liệu chính xác. Tập lệnh chỉ phục vụ đọc cấu trúc biểu mẫu và điền dữ liệu
        theo thao tác của người dùng; không thu thập dữ liệu từ trang ngoài phạm vi Dịch vụ công đã khai
        báo và không theo dõi hành vi duyệt web.</p>

      <h2>12. Chia sẻ dữ liệu với bên thứ ba</h2>
      <p>Chúng tôi không bán, không cho thuê và không chia sẻ dữ liệu người dùng với bên thứ ba cho mục
        đích quảng cáo, tiếp thị, phân tích hành vi, môi giới dữ liệu hoặc chấm điểm tín dụng. Chúng tôi
        chỉ có thể tiết lộ dữ liệu khi: (a) có yêu cầu hợp lệ theo quy định pháp luật hoặc từ cơ quan có
        thẩm quyền; (b) cần bảo vệ quyền, tài sản, an toàn hệ thống hoặc ngăn chặn gian lận/lạm dụng;
        (c) người dùng hoặc đơn vị quản lý yêu cầu hỗ trợ kỹ thuật và đồng ý cung cấp dữ liệu cần thiết.</p>

      <h2>13. Truy cập dữ liệu bởi nhân sự vận hành</h2>
      <p>Chúng tôi không cho phép nhân sự đọc dữ liệu người dùng, trừ khi cần thiết để: hỗ trợ kỹ thuật
        theo yêu cầu và có sự đồng ý; kiểm tra/khắc phục lỗi hệ thống; bảo mật, phát hiện lạm dụng hoặc
        điều tra truy cập bất thường; tuân thủ yêu cầu pháp luật. Trong các trường hợp này, quyền truy
        cập được giới hạn theo phạm vi và mục đích cần thiết.</p>

      <h2>14. Quyền của người dùng</h2>
      <ul>
        <li>Yêu cầu biết dữ liệu tài khoản liên quan đến mình đang được lưu (thông tin tài khoản, phiên
          đăng nhập).</li>
        <li>Yêu cầu chỉnh sửa dữ liệu tài khoản không chính xác nếu có cơ chế hỗ trợ phù hợp.</li>
        <li>Yêu cầu xóa dữ liệu tài khoản liên quan đến mình, trừ trường hợp phải tiếp tục lưu theo quy
          định pháp luật hoặc yêu cầu vận hành bắt buộc.</li>
        <li>Đăng xuất khỏi Tiện ích để xóa dữ liệu phiên cục bộ.</li>
        <li>Gỡ Tiện ích khỏi trình duyệt bất cứ lúc nào.</li>
      </ul>

      <h2>15. Đối tượng sử dụng</h2>
      <p>Tiện ích dành cho cán bộ, nhân sự hoặc người dùng được cấp tài khoản để xử lý hồ sơ hành chính
        công. Tiện ích không dành cho trẻ em và không chủ đích thu thập dữ liệu của trẻ em.</p>

      <h2>16. Thay đổi chính sách quyền riêng tư</h2>
      <p>Chúng tôi có thể cập nhật chính sách này khi có thay đổi về tính năng, quy trình xử lý dữ liệu,
        yêu cầu pháp luật hoặc yêu cầu từ nền tảng phân phối Tiện ích. Khi có thay đổi quan trọng, chúng
        tôi sẽ cập nhật ngày &ldquo;Cập nhật lần cuối&rdquo; ở đầu tài liệu và có thể thông báo trong
        Tiện ích hoặc qua kênh phù hợp.</p>

      <h2>17. Tuân thủ Limited Use của Chrome Web Store</h2>
      <div class="callout">
        <p>Việc sử dụng dữ liệu của Tiện ích tuân thủ Chrome Web Store User Data Policy, bao gồm các yêu
          cầu Limited Use. Tiện ích chỉ thu thập, sử dụng và truyền dữ liệu người dùng trong phạm vi cần
          thiết để cung cấp hoặc cải thiện mục đích chính đã công bố: hỗ trợ trích xuất thông tin từ giấy
          tờ và điền biểu mẫu Dịch vụ công. Ảnh, tệp PDF, âm thanh và nội dung trích xuất chỉ được xử lý
          tức thời và không được máy chủ lưu trữ lại sau khi hoàn tất.</p>
        <p>Tiện ích không sử dụng hoặc chuyển dữ liệu người dùng cho quảng cáo cá nhân hóa, tiếp thị lại,
          môi giới dữ liệu, bán dữ liệu, đánh giá khả năng tín dụng hoặc cho vay.</p>
      </div>
    </main>

    <footer>&copy; __ORG__ — Chính sách quyền riêng tư tiện ích &ldquo;Trợ lý người dân&rdquo;.</footer>
  </div>
</body>
</html>"""


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy() -> HTMLResponse:
    """Trang chính sách công khai (không auth) dán vào Chrome Web Store."""
    phone = (settings.legal_contact_phone or "").strip()
    phone_row = (
        f'<li>Điện thoại: <a href="tel:{phone}">{phone}</a></li>' if phone else ""
    )
    html = (
        _PRIVACY_HTML
        .replace("__ORG__", settings.legal_org_name)
        .replace("__EMAIL__", settings.legal_contact_email)
        .replace("__PHONE_ROW__", phone_row)
        .replace("__UPDATED__", settings.privacy_updated)
    )
    return HTMLResponse(content=html)
