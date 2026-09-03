# Handfree channel

Thư mục này chỉ chứa phần khác biệt về trải nghiệm Handfree: hội thoại, trạng thái luồng,
metadata card/checklist, thông tin chủ hồ sơ và giao diện tải giấy tờ trên điện thoại.

Các pipeline nghiệp vụ `process` và `attach` không được sao chép. Registry Handfree ủy
quyền trực tiếp về `app.procedures.registry`, nhờ đó Auto Fill và Handfree dùng cùng một
core cho 15 thủ tục đang mở trên trợ lý.

Entry point được kiểm soát bởi `HANDFREE_ENABLED`:

- Chat: `/api/v1/assistant/*`
- Phiên giấy tờ: `/api/v1/assistant/document-sessions/*`
- Mobile Handfree: `/m/handfree/{sid}`
- Mobile Auto Fill: `/m/autofill/{sid}`
- Cấu hình voice: `/api/v1/voice/config`
- ASR/TTS Handfree: `/ws/asr`, `/ws/tts`

REST Handfree bắt buộc Bearer và mọi `conversation_id`/document session đều được đối
chiếu với `auth_user.id`. WebSocket ASR/TTS nhận access JWT bằng subprotocol
`tlnd-auth.<jwt>` (không đặt token trong URL); extension phải lấy token còn hạn trước mỗi
lượt mở socket. Mobile QR dùng capability riêng theo session, còn ảnh review dùng
capability ngắn hạn theo request; hai token không dùng thay cho nhau.

Các route `/api/v1/upload-sessions/*` cũ vẫn có adapter cho extension Handfree hiện tại
trong giai đoạn chuyển tiếp. Session lưu field `experience` để hai giao diện không đọc
nhầm dữ liệu của nhau.
