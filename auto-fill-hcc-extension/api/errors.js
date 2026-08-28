// 1 NGUỒN CHÂN LÝ cho thông điệp lỗi hiển thị lên UI extension.
//
// Nguyên tắc: FE tra MÃ lỗi BE (ổn định) → câu tiếng Việt cố định. KHÔNG BAO GIỜ in text kỹ thuật
// thô (traceback, JSON, lỗi JS/DOM, log OpenAI/OCR...). Không khớp mã/không an toàn → câu chung.
// Chi tiết kỹ thuật chỉ để console.warn + mã hỗ trợ (requestId) cho cán bộ báo lỗi.

const GENERIC_ERROR = "Không thực hiện được thao tác. Vui lòng thử lại.";

// Map MÃ lỗi (AppError.error ở BE) → câu người dùng đọc được.
const ERROR_MESSAGES = {
  INTERNAL_ERROR: "Hệ thống gặp lỗi khi xử lý. Vui lòng thử lại sau.",
  PIPELINE_ERROR: "Không xử lý được giấy tờ. Kiểm tra lại ảnh/tệp rồi thử lại.",
  NO_FILES: "Chưa có tệp nào để xử lý.",
  FILE_TOO_LARGE: "Tệp vượt quá dung lượng cho phép.",
  PAYLOAD_TOO_LARGE: "Tổng dung lượng các tệp quá lớn.",
  BAD_FILE_TYPE: "Loại tệp này không được hỗ trợ.",
  FILE_NOT_FOUND: "Không tìm thấy tệp.",
  // BE ném mã này cho CẢ hai trường hợp: key thủ tục lạ, VÀ thủ tục có trong registry nhưng chưa có
  // pipeline bóc tách (chưa khai ở _PIPELINE). Câu cũ "Thủ tục không hợp lệ." sai bản chất ở vế sau —
  // cán bộ thấy panel nhận diện đúng tên thủ tục rồi lại báo không hợp lệ nên tưởng hỏng nhận diện.
  UNKNOWN_PROCEDURE: "Thủ tục này chưa hỗ trợ quét và nhập dữ liệu tự động.",
  UNKNOWN_ATTACHMENT_PROCEDURE: "Thủ tục này chưa hỗ trợ đính kèm.",
  UNSUPPORTED_ATTACHMENT_PROCEDURE: "Thủ tục này chưa hỗ trợ đính kèm.",
  SESSION_NOT_FOUND: "Phiên đã hết hạn. Vui lòng tạo phiên/mã QR mới.",
  SESSION_PROCEDURE_MISMATCH: "Phiên không khớp thủ tục đang chọn.",
  INVALID_CREDENTIALS: "Sai tên đăng nhập hoặc mật khẩu.",
  INVALID_REFRESH: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  TOKEN_EXPIRED: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  MISSING_TOKEN: "Vui lòng đăng nhập để tiếp tục.",
  FORBIDDEN: "Bạn không có quyền thực hiện thao tác này.",
  NOT_ADMIN: "Bạn không có quyền quản trị.",
  USER_NOT_FOUND: "Không tìm thấy người dùng.",
  USERNAME_EXISTS: "Tên đăng nhập đã tồn tại.",
  CANNOT_DELETE_SELF: "Không thể tự xoá tài khoản đang đăng nhập.",
  BAD_ROLE: "Vai trò không hợp lệ.",
  BAD_DATE: "Ngày không hợp lệ.",
  BAD_CONSENT: "Chưa ghi nhận được sự đồng ý.",
  TRACE_NOT_FOUND: "Không tìm thấy dữ liệu.",
  REVIEW_NOT_FOUND: "Không tìm thấy dữ liệu rà soát.",
  REVIEW_IMAGE_NOT_FOUND: "Không tìm thấy ảnh.",
};

// Không có mã → tra theo HTTP status / lỗi mạng (status 0).
const STATUS_MESSAGES = {
  0: "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.",
  400: "Dữ liệu gửi lên không hợp lệ.",
  422: "Dữ liệu gửi lên không hợp lệ.",
  401: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.",
  403: "Bạn không có quyền thực hiện thao tác này.",
  404: "Không tìm thấy dữ liệu.",
  408: "Xử lý quá lâu. Vui lòng thử lại.",
  413: "Tệp/dữ liệu quá lớn.",
  429: "Hệ thống đang quá tải. Thử lại sau ít phút.",
  500: "Máy chủ gặp lỗi. Vui lòng thử lại sau.",
  502: "Máy chủ đang bận. Vui lòng thử lại sau.",
  503: "Máy chủ đang bận. Vui lòng thử lại sau.",
  504: "Xử lý quá lâu. Vui lòng thử lại.",
};

// Dấu hiệu text KỸ THUẬT (không được hiển thị): JSON, traceback, URL, lỗi JS phổ biến, mã req...
const TECH_NOISE =
  /[{}[\]]|traceback|exception|error code|req_[a-z0-9]{6,}|https?:\/\/|http\/?\s?\d{3}|net::|failed to fetch|networkerror|econnrefused|\bstack\b|undefined is not|cannot read|is not a function|"[a-z_]+"\s*:/i;

// Trả câu nếu là 1 câu tiếng Việt SẠCH, đủ ngắn, không mùi kỹ thuật; ngược lại "".
function safeSentence(s) {
  const t = String(s == null ? "" : s).replace(/\s+/g, " ").trim();
  if (!t || t.length > 160) return "";
  if (TECH_NOISE.test(t)) return "";
  if (!/[a-zà-ỹ]/i.test(t)) return ""; // toàn số/ký hiệu → không phải câu
  return t;
}

// input: Error (ưu tiên .data.error = mã BE) HOẶC string. Luôn trả 1 câu an toàn.
function friendlyError(input) {
  if (input && typeof input === "object") {
    const code = input.data && input.data.error;
    if (code && ERROR_MESSAGES[code]) return ERROR_MESSAGES[code];   // 1. mã lỗi BE (kiểm soát)
    if (input.unauthorized) return ERROR_MESSAGES.TOKEN_EXPIRED;
    // 2. message AppError cụ thể (nếu sạch) — ưu tiên hơn câu status chung để giữ lý do nghiệp vụ.
    const safe = safeSentence((input.data && input.data.message) || input.message);
    if (safe) return safe;
    // 3. theo HTTP status / mạng.
    const status = typeof input.status === "number" ? input.status : null;
    if (status != null && STATUS_MESSAGES[status]) return STATUS_MESSAGES[status];
    return GENERIC_ERROR;
  }
  return safeSentence(input) || GENERIC_ERROR;
}

// Mã hỗ trợ (BE gắn ở lỗi 500) để cán bộ đọc cho kỹ thuật tra log. null nếu không có.
function errorSupportCode(input) {
  return (input && typeof input === "object" && input.data && input.data.requestId) || null;
}

if (typeof window !== "undefined") {
  window.ERROR_MESSAGES = ERROR_MESSAGES;
  window.friendlyError = friendlyError;
  window.errorSupportCode = errorSupportCode;
}
