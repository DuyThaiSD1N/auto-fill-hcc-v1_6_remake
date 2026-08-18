/**
 * Link trang kê khai của từng thủ tục trên Cổng DVC quốc gia.
 *
 * Nguồn: tro-ly-nguoi-dan-backend/app/procedures/registry.py (field `keKhaiUrl`) — chỉ những thủ tục
 * CÓ link mới nằm ở đây. `key` trùng key thủ tục của auto-fill-hcc-backend nên chọn ở thanh này là
 * chọn luôn đúng pipeline điền tự động.
 *
 * `needsAgencySelect`: cổng React mới bắt chọn Tỉnh/Xã + "Nộp trực tuyến" trước khi vào biểu mẫu →
 * dùng địa chỉ đã lưu ở mục "Đi đến thủ tục".
 *
 * `autoConfirm`: vào hồ sơ xong cổng còn chặn modal "Thông tin chung" → trợ lý bấm "Xác nhận" hộ để
 * đi thẳng vào wizard (tương ứng action `confirm_info_modal` của tro-ly-nguoi-dan-backend). Thủ tục
 * nào không muốn tự bấm thì để false — chuỗi sẽ dừng ngay sau "Nộp trực tuyến".
 */
window.PROCEDURE_KE_KHAI_LINKS = [
  {
    key: "khai-sinh-dang-ky",
    label: "Liên thông đăng ký khai sinh, thường trú, BHYT cho trẻ dưới 6 tuổi",
    url: "https://lienthong.dichvucong.gov.vn/#/ke-khai/2.000986",
    needsAgencySelect: false,
    autoConfirm: false,
  },
  {
    key: "ket-hon",
    label: "Thủ tục đăng ký kết hôn",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fac-7489-b53b-a15eb239a6fe",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "dang-ky-lai-ket-hon",
    label: "Thủ tục đăng ký lại kết hôn",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6711-733d-b674-f82cb6606242",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "ket-hon-nuoc-ngoai",
    label: "Thủ tục đăng ký kết hôn có yếu tố nước ngoài",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e13-728a-a0cd-635811d8432e",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "khai-sinh-dang-ky-lai",
    label: "Thủ tục đăng ký lại khai sinh",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6eac-7598-b88b-15f8a61b366a",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "khai-tu",
    label: "Thủ tục đăng ký khai tử",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fac-7489-b53b-9c6c958f2da4",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "khai-tu-dang-ky-lai",
    label: "Thủ tục đăng ký lại khai tử",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6ebc-709e-8678-a9f8b66738f2",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "dang-ky-giam-ho",
    label: "Thủ tục đăng ký giám hộ",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-671b-75fa-82fb-8ad05a37f638",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "dang-ky-nhan-cha-me-con",
    label: "Thủ tục đăng ký nhận cha, mẹ, con",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-3fa6-722f-ac1a-e949c8ce3418",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "xac-nhan-tinh-trang-hon-nhan",
    label: "Thủ tục cấp Giấy xác nhận tình trạng hôn nhân",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-6eb3-7019-bf3f-fc58c9ee44b9",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "trich-luc-ks",
    label: "Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-867c-72db-b6a7-dcbd8c763807",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "chung-thuc-ban-sao",
    label: "Chứng thực bản sao từ bản chính giấy tờ, văn bản",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e22-77ef-819f-e49460350904",
    needsAgencySelect: true,
    autoConfirm: true,
  },
  {
    key: "chung-thuc-chu-ky",
    label: "Chứng thực chữ ký trong các giấy tờ, văn bản",
    url: "https://dichvucong.gov.vn/thu-tuc-hanh-chinh/019d2bfd-8e2e-7359-b42f-d5dc8d74741b",
    needsAgencySelect: true,
    autoConfirm: true,
  },
];
