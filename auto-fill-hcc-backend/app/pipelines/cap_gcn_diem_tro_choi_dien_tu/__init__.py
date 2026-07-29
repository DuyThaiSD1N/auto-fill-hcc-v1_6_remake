"""Pipeline "Cấp giấy chứng nhận đủ điều kiện hoạt động điểm cung cấp dịch vụ trò chơi điện tử
công cộng" (MaTTHC 1.013792 — cổng Bộ VHTTDL dichvucong.bvhttdl.gov.vn).

Nền tảng MỚI: Angular Material của cổng bvhttdl (custom element `liz-input`/`liz-datepicker`/
`liz-select`) — DOM đã STRIP formcontrolname → engine `content/fill-liz.js` khớp ô theo
(nhãn section `.group-header`, nhãn `<mat-label>`), KHÔNG dùng id `mat-input-N` (lệch giữa render).

Chủ điểm là CÁ NHÂN → người nộp (Phần II) = người được giải quyết (Phần III) = chủ hộ kinh doanh
(người đại diện pháp luật, Phần IV) là CÙNG một người. Nguồn: CCCD + Đơn đề nghị (Mẫu 51a) +
Giấy phép kinh doanh (GCN đăng ký hộ kinh doanh). Phần I "Thông tin chung" hệ thống tự điền (disabled).
"""
