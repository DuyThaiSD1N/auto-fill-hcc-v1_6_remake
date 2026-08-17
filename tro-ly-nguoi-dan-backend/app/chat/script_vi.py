"""Lời thoại tiếng Việt của bot — TÁCH KHỎI logic (docs/03a §3, giọng theo prototype).

Quy ước: mỗi mục có `md` (hiện trong chat, được dùng markdown) và `tts` (đọc loa —
KHÔNG markdown, câu ngắn, số/tên đọc được). Sửa giọng điệu chỉ sửa file này.
{Chỗ trống} được flow.format() điền bằng str.format — đừng đổi tên biến trong ngoặc.
"""

GREET = {
    "md": (
        "**Xin chào bà con!** Em là **Trợ lý người dân**, hỗ trợ làm thủ tục hành chính công ạ.\n\n"
        "Bà con kiểm tra **nơi làm thủ tục** bên dưới rồi **chọn thủ tục** cần làm — "
        "bấm vào thẻ hoặc gõ/nói tên thủ tục đều được ạ."
    ),
    "tts": (
        "Xin chào bà con em là Trợ lý người dân. "
        "Bà con chọn thủ tục cần làm, bấm vào thẻ hoặc nói tên thủ tục đều được ạ."
    ),
}

GREET_RETURNING = {
    "md": "Bà con đang làm dở thủ tục **{procedure}** (đến bước: {step_label}). Bà con muốn **tiếp tục** hay **làm thủ tục khác** ạ?",
    "tts": "Bà con đang làm dở thủ tục {procedure}. Bà con muốn tiếp tục hay làm thủ tục khác ạ?",
}

CONFIRM_PROCEDURE = {
    "md": "Dạ, bà con muốn làm **{procedure}** tại **{ward}, {province}** đúng không ạ?",
    "tts": "Dạ bà con muốn làm thủ tục {procedure} tại {ward} {province} đúng không ạ?",
}

PROCEDURE_NOT_RECOGNIZED = {
    "md": (
        "Dạ em chưa nhận ra thủ tục bà con cần ạ. Hiện em hỗ trợ **{count} thủ tục** trong danh sách bên dưới — "
        "bà con bấm chọn hoặc nói lại tên giúp em nhé."
    ),
    "tts": "Dạ em chưa nhận ra thủ tục bà con cần. Bà con chọn trong danh sách hoặc nói lại tên giúp em nhé.",
}

GUIDE_LOGIN = {
    "md": (
        "Em đang đưa bà con sang trang thủ tục. Nếu trang yêu cầu đăng nhập, bà con mở app **VNeID** "
        "trên điện thoại → chọn **Quét QR** → quét mã trên màn hình để đăng nhập ạ.\n\n"
        "Đăng nhập xong em sẽ tự nhận ra và hướng dẫn tiếp 😊"
    ),
    "tts": (
        "Bà con mở app VNeID trên điện thoại chọn Quét QR, rồi quét mã trên màn hình để đăng nhập. "
        "Đăng nhập xong em sẽ hướng dẫn tiếp ạ."
    ),
}

GUIDE_AGENCY_SELECT = {
    "md": (
        "Em đang mở trang thủ tục **{procedure}**. Em sẽ **tự chọn cơ quan thực hiện** "
        "(**{ward}, {province}**) và bấm **Nộp trực tuyến** giúp bà con."
    ),
    "tts": "Em đang mở trang thủ tục và sẽ tự chọn cơ quan {ward}, {province} rồi bấm nộp trực tuyến giúp bà con.",
}

# Chọn cơ quan xong — 2 nhánh theo trạng thái đăng nhập THẤY trên trang, không nói phòng hờ.
AGENCY_DONE_LOGGED_IN = {
    "md": (
        "✅ Em đã chọn cơ quan **{ward}, {province}** và bấm **Nộp trực tuyến**. "
        "Em thấy bà con **đã đăng nhập sẵn** nên mình vào thẳng trang kê khai ạ…"
    ),
    "tts": (
        "Em đã chọn cơ quan và bấm nộp trực tuyến rồi ạ. "
        "Bà con đã đăng nhập sẵn nên mình vào thẳng trang kê khai nhé."
    ),
}

# Liên thông: trang "Chọn cơ quan thực hiện" (Angular, KHÔNG có needsAgencySelect nên bot không
# tự chọn) → dặn người dân chọn tỉnh/xã + bấm tiếp, nói 1 lần; sang trang kê khai thì thôi.
AGENCY_MANUAL_GUIDE = {
    "md": (
        "Dạ, bà con **chọn cơ quan thực hiện** (tỉnh/xã) trên trang rồi bấm **tiếp tục** giúp em ạ "
        "— sang bước **kê khai** em hướng dẫn tiếp ngay 😊"
    ),
    "tts": (
        "Dạ bà con chọn cơ quan thực hiện gồm tỉnh và xã trên trang rồi bấm tiếp tục ạ. "
        "Sang bước kê khai em hướng dẫn tiếp ngay."
    ),
}

# Trợ lý ĐIỀN HỘ bước chọn cơ quan (liên thông khai sinh): loại khai sinh, tỉnh/xã theo nơi ở,
# trường hợp khai sinh/ĐKTT, tick "Cùng địa bàn". Điền xong người dân tự bấm "Chuyển bước tiếp theo".
AGENCY_AUTOFILL_GUIDE = {
    "md": (
        "Dạ, em **chọn giúp** bà con **cơ quan thực hiện** (khai sinh, thường trú, BHYT) theo nơi ở "
        "**{ward}, {province}** ạ. Chọn xong bà con bấm **Chuyển bước tiếp theo** giúp em nhé 😊"
    ),
    "tts": (
        "Dạ, em chọn giúp bà con cơ quan thực hiện theo nơi ở của bà con. "
        "Xong bà con bấm Chuyển bước tiếp theo giúp em ạ."
    ),
}

# MỘT CÂU duy nhất đọc TRÊN chính trang login SSO (Hướng A): xác nhận cơ quan + dặn VNeID/Quét QR
# gộp lại (không tách 2 bong bóng). Panel còn hiện → đọc đủ → đọc xong FE thu gọn
# (action collapse_after_tts ở flow) để lộ mã QR cho bà con quét.
QR_LOGIN_GUIDE = {
    "md": (
        "✅ Em đã chọn cơ quan **{ward}, {province}** và mở bước **đăng nhập** ạ. "
        "Bà con mở app **VNeID** trên điện thoại → chọn **Quét QR** → quét mã trên màn hình "
        "để đăng nhập ạ. Xong em hướng dẫn tiếp ngay 😊"
    ),
    "tts": (
        "Em đã chọn cơ quan {ward}, {province} và mở bước đăng nhập ạ. "
        "Bà con mở app VNeID chọn Quét QR rồi quét mã trên màn hình để đăng nhập. Xong em hướng dẫn tiếp ạ."
    ),
}

# Người dân gõ/nói giữa lúc chờ — nhắc NGẮN theo đúng việc đang chờ, kèm nút phao.
WAIT_LOGIN_REMIND = {
    "md": (
        "Dạ, em đang chờ bà con **đăng nhập VNeID** ạ — mở app → **Quét QR** giúp em nhé. "
        "Nếu đã vào được trang kê khai mà em chưa nhận ra, bà con bấm nút dưới ạ."
    ),
    "tts": "Dạ em đang chờ bà con đăng nhập ạ. Nếu đã vào được trang kê khai, bà con bấm nút trên màn hình giúp em nhé.",
}

WAIT_PORTAL_REMIND = {
    "md": (
        "Dạ, em đang chờ trang chuyển sang **bước kê khai** ạ. "
        "Nếu bà con đã thấy form kê khai mà em chưa nhận ra, bấm nút dưới giúp em nhé."
    ),
    "tts": (
        "Dạ em đang chờ trang chuyển sang bước kê khai ạ. "
        "Nếu bà con đã thấy form kê khai mà em chưa nhận ra, bấm nút trên màn hình giúp em nhé."
    ),
}

WAIT_ATTACH_PORTAL_REMIND = {
    "md": (
        "Dạ, em đang chờ trang chuyển sang **Thành phần hồ sơ** ạ. Nếu bà con đã thấy bảng "
        "đính kèm mà em chưa nhận ra, bấm nút dưới giúp em nhé."
    ),
    "tts": (
        "Dạ em đang chờ trang chuyển sang thành phần hồ sơ ạ. Nếu bà con đã thấy bảng đính kèm, "
        "bấm nút trên màn hình giúp em nhé."
    ),
}

AGENCY_SELECT_FAILED = {
    "md": (
        "⚠️ Em chưa chọn được cơ quan tự động: *{error}*\n\n"
        "Bà con chọn tay giúp em: **{ward}, {province}** rồi bấm **Đồng ý** ạ."
    ),
    "tts": "Em chưa chọn tự động được bà con chọn tay giúp em rồi bấm đồng ý ạ.",
}

GUIDE_LOGIN_NO_URL = {
    "md": (
        "Dạ thủ tục **{procedure}** em chưa có sẵn đường dẫn trang kê khai. "
        "Bà con mở trang thủ tục trên cổng dịch vụ công giúp em, em sẽ tự nhận ra và hỗ trợ tiếp ạ."
    ),
    "tts": "Bà con mở trang thủ tục trên cổng dịch vụ công giúp em, em sẽ tự nhận ra và hỗ trợ tiếp ạ.",
}

# intro: "Đăng nhập thành công ✓" (nhánh phải đăng nhập) / "Đã vào trang kê khai ✓" (đăng nhập sẵn).
ASK_DOC_METHOD = {
    "md": (
        "{intro_md} Để làm **{procedure}**, bà con cần chuẩn bị giấy tờ sau:\n\n{doc_list}\n\n"
        "**Bà con sẽ cung cấp giấy tờ bằng cách nào ạ?** Chọn 1 cách bên dưới:"
    ),
    "tts": (
        "{intro_tts} Bà con cần chuẩn bị: {doc_list_tts}. "
        "Bà con muốn cung cấp giấy tờ bằng cách nào ạ? Chụp bằng điện thoại hay scan tại quầy ạ?"
    ),
}

INTRO_LOGIN_OK = {"md": "Đăng nhập thành công ✓", "tts": "Đăng nhập thành công rồi ạ."}
INTRO_FORM_REACHED = {"md": "Đã vào trang kê khai ✓", "tts": "Mình đã vào trang kê khai rồi ạ."}
INTRO_ATTACH_REACHED = {
    "md": "Đã vào bước Thành phần hồ sơ ✓",
    "tts": "Mình đã vào bước thành phần hồ sơ rồi ạ.",
}

# Wizard hồ sơ cổng React (kết hôn): modal "Thông tin chung" → bước Thông tin chủ hồ sơ
# → bước Kê khai. Modal đã điền sẵn đúng cơ quan → bot bấm Xác nhận hộ LẶNG LẼ (không báo câu —
# đã bỏ CONFIRM_INFO_MODAL khỏi luồng theo yêu cầu; hành động confirm_info_modal vẫn chạy ở flow).

OWNER_INFO_GUIDE = {
    "md": (
        "Bà con điền **Thông tin chủ hồ sơ** (số điện thoại, thư điện tử, địa chỉ) rồi bấm "
        "nút tiếp tục của trang để sang **bước kê khai** giúp em ạ — vào đến nơi em hướng dẫn tiếp ngay 😊"
    ),
    "tts": (
        "Bà con điền thông tin chủ hồ sơ gồm số điện thoại, thư điện tử, địa chỉ, "
        "rồi bấm tiếp tục để sang bước kê khai ạ. Vào đến nơi em hướng dẫn tiếp ngay."
    ),
}

OWNER_INFO_ATTACH_GUIDE = {
    "md": (
        "Bà con điền **Thông tin chủ hồ sơ** (số điện thoại, thư điện tử, địa chỉ) rồi bấm "
        "nút tiếp tục của trang giúp em ạ, trang sẽ "
        "chuyển tới **Thành phần hồ sơ** và em hướng dẫn đính kèm ngay 😊"
    ),
    "tts": (
        "Bà con điền thông tin chủ hồ sơ gồm số điện thoại, thư điện tử, địa chỉ rồi bấm tiếp tục ạ. "
        "Trang sẽ chuyển tới thành phần hồ sơ."
    ),
}

# ── Xin phép xử lý dữ liệu cá nhân (Luật 91/2025/QH15) — TRƯỚC khi nhận/đọc giấy tờ ──
# intro: nối mốc "Đăng nhập thành công ✓ / Đã vào trang kê khai ✓" như ASK_DOC_METHOD.
CONSENT_INTRO = {
    "md": (
        "{intro_md} Trước khi nhận và đọc giấy tờ, em cần **bà con cho phép xử lý dữ liệu "
        "cá nhân** ạ. Bà con đọc nội dung trong thẻ dưới đây, tích **2 ô xác nhận** rồi bấm "
        "**Đồng ý và tự động điền** nhé. Nếu không đồng ý, bà con chọn **Tự nhập** — "
        "em sẽ không đọc giấy tờ ạ."
    ),
    "tts": (
        "{intro_tts} Trước khi nhận và đọc giấy tờ, em cần bà con cho phép xử lý dữ liệu cá nhân ạ. "
        "Trong thủ tục này em sẽ chỉ đọc: {doc_list_tts}, để tự động điền biểu mẫu và chuẩn bị "
        "tệp đính kèm. Bà con đọc nội dung trong thẻ, tích hai ô xác nhận, rồi bấm Đồng ý và tự động điền. "
        "Nếu không đồng ý, bà con chọn tự nhập, em sẽ không đọc giấy tờ ạ."
    ),
}

CONSENT_ATTACH_INTRO = {
    "md": (
        "{intro_md} Trước khi nhận và tự động đính kèm giấy tờ, em cần **bà con cho phép xử lý "
        "dữ liệu cá nhân** ạ. Bà con đọc nội dung trong thẻ dưới đây, tích **2 ô xác nhận** rồi "
        "bấm **Đồng ý và tự động đính kèm** nhé."
    ),
    "tts": (
        "{intro_tts} Trước khi nhận và tự động đính kèm {doc_list_tts}, em cần bà con cho phép "
        "xử lý dữ liệu cá nhân ạ. Bà con đọc nội dung trong thẻ, tích hai ô xác nhận rồi bấm đồng ý."
    ),
}

# Nội dung hiển thị TRONG card consent_form — server-driven, FE chỉ render.
CONSENT_CARD_TEXT = {
    "intro_md": (
        "Chỉ khi bà con bấm **Đồng ý và tự động điền**, em mới đọc, trích xuất và xử lý "
        "thông tin cần thiết từ các giấy tờ dưới đây, rồi tự động điền vào biểu mẫu trên trang."
    ),
    "scope_md": (
        "Em chỉ đọc thông tin cần thiết từ giấy tờ **bà con chủ động cung cấp** cho thủ tục này. "
        "Bà con kiểm tra và sửa được toàn bộ dữ liệu trước khi nộp hồ sơ."
    ),
    "purpose_md": (
        "**Mục đích chia sẻ, xử lý dữ liệu:** đọc chữ trên ảnh (OCR), chuẩn hoá thông tin, "
        "tự động điền biểu mẫu và chuẩn bị tệp đính kèm; dữ liệu chỉ được **chia sẻ lên "
        "Cổng Dịch vụ công** để nộp hồ sơ theo yêu cầu của bà con. Hồ sơ đã xử lý "
        "(ảnh giấy tờ, kết quả đọc) được **lưu trên hệ thống** phục vụ đối soát và "
        "hỗ trợ giải quyết thủ tục."
    ),
    "checks": [
        "Tôi đã đọc, hiểu phạm vi giấy tờ, thông tin được xử lý và mục đích nêu trên; "
        "đồng ý cho Trợ lý người dân đọc, xử lý và tự động điền dữ liệu vào biểu mẫu.",
        "Tôi xác nhận tự chịu trách nhiệm về tính chính xác, hợp pháp của các thông tin "
        "nêu trên và về việc thực hiện thủ tục hành chính của mình.",
    ],
    "accept_label": "Đồng ý và tự động điền",
    "decline_label": "Không đồng ý · Tự nhập",
}

CONSENT_ATTACH_CARD_TEXT = {
    "intro_md": (
        "Chỉ khi bà con bấm **Đồng ý và tự động đính kèm**, em mới nhận các tệp bà con chủ động "
        "cung cấp và gắn chúng vào hồ sơ trên Cổng Dịch vụ công."
    ),
    "scope_md": (
        "Thủ tục này chỉ dùng **một loại giấy tờ** và không phân loại nội dung. Bà con có thể gửi "
        "nhiều tệp; tất cả được xử lý trong cùng một hồ sơ."
    ),
    "purpose_md": (
        "**Mục đích xử lý dữ liệu:** lưu tạm các tệp trong phiên làm thủ tục và tự động đính kèm "
        "chúng lên Cổng Dịch vụ công theo yêu cầu của bà con; không trích xuất dữ liệu để điền biểu mẫu."
    ),
    "checks": [
        "Tôi đã đọc, hiểu phạm vi giấy tờ và mục đích xử lý nêu trên; đồng ý cho Trợ lý người dân "
        "nhận, lưu tạm và tự động đính kèm các tệp tôi cung cấp vào hồ sơ.",
        "Tôi xác nhận tự chịu trách nhiệm về tính chính xác, hợp pháp của các giấy tờ đã cung cấp "
        "và về việc thực hiện thủ tục hành chính của mình.",
    ],
    "accept_label": "Đồng ý và tự động đính kèm",
    "decline_label": "Không đồng ý · Tự đính kèm",
}

# Toàn văn Điều 4 Luật 91/2025/QH15 — FE để trong khối mở rộng (details).
CONSENT_LEGAL_MD = """*Theo Luật số 91/2025/QH15 ngày 26/6/2025 — Luật Bảo vệ dữ liệu cá nhân*

**Điều 4. Quyền và nghĩa vụ của chủ thể dữ liệu cá nhân**

**1. Quyền của chủ thể dữ liệu cá nhân bao gồm:**

- a) Được biết về hoạt động xử lý dữ liệu cá nhân;
- b) Đồng ý hoặc không đồng ý, yêu cầu rút lại sự đồng ý cho phép xử lý dữ liệu cá nhân;
- c) Xem, chỉnh sửa hoặc yêu cầu chỉnh sửa dữ liệu cá nhân;
- d) Yêu cầu cung cấp, xóa, hạn chế xử lý dữ liệu cá nhân; gửi yêu cầu phản đối xử lý dữ liệu cá nhân;
- đ) Khiếu nại, tố cáo, khởi kiện, yêu cầu bồi thường thiệt hại theo quy định của pháp luật;
- e) Yêu cầu cơ quan có thẩm quyền hoặc cơ quan, tổ chức, cá nhân liên quan đến xử lý dữ liệu cá nhân thực hiện các biện pháp, giải pháp bảo vệ dữ liệu cá nhân của mình theo quy định của pháp luật.

**2. Nghĩa vụ của chủ thể dữ liệu cá nhân bao gồm:**

- a) Tự bảo vệ dữ liệu cá nhân của mình;
- b) Tôn trọng, bảo vệ dữ liệu cá nhân của người khác;
- c) Cung cấp đầy đủ, chính xác dữ liệu cá nhân của mình theo quy định của pháp luật, theo hợp đồng hoặc khi đồng ý cho phép xử lý dữ liệu cá nhân của mình;
- d) Chấp hành pháp luật về bảo vệ dữ liệu cá nhân và tham gia phòng, chống hoạt động xâm phạm dữ liệu cá nhân.

**3. Chủ thể dữ liệu cá nhân khi thực hiện quyền và nghĩa vụ của mình phải tuân thủ đầy đủ các nguyên tắc sau đây:**

- a) Thực hiện theo quy định của pháp luật; tuân thủ nghĩa vụ của chủ thể dữ liệu cá nhân theo hợp đồng. Việc thực hiện quyền và nghĩa vụ của chủ thể dữ liệu cá nhân phải nhằm mục đích bảo vệ quyền, lợi ích hợp pháp của chính chủ thể dữ liệu cá nhân đó;
- b) Không được gây khó khăn, cản trở việc thực hiện quyền, nghĩa vụ pháp lý của bên kiểm soát dữ liệu cá nhân, bên kiểm soát và xử lý dữ liệu cá nhân, bên xử lý dữ liệu cá nhân;
- c) Không được xâm phạm đến quyền, lợi ích hợp pháp của Nhà nước, cơ quan, tổ chức và cá nhân khác.

**4.** Cơ quan, tổ chức, cá nhân có trách nhiệm tạo điều kiện thuận lợi, không được gây khó khăn, cản trở việc thực hiện quyền và nghĩa vụ của chủ thể dữ liệu cá nhân theo quy định của pháp luật.

**5.** Khi nhận được yêu cầu của chủ thể dữ liệu cá nhân để thực hiện quyền của chủ thể dữ liệu cá nhân quy định tại khoản 1 Điều này, bên kiểm soát dữ liệu cá nhân, bên kiểm soát và xử lý dữ liệu cá nhân phải kịp thời thực hiện trong thời hạn theo quy định của pháp luật."""

CONSENT_ACCEPTED = {
    "md": (
        "✅ Đã ghi nhận sự đồng ý của bà con — mã nhật ký **{log_id}**, lúc {time}, "
        "bản nội dung v{version}."
    ),
    "tts": "Em đã ghi nhận sự đồng ý của bà con rồi ạ.",
}

CONSENT_DECLINED = {
    "md": (
        "Dạ em tôn trọng quyết định của bà con ✓ Em sẽ **không đọc và không xử lý** giấy tờ nào. "
        "Bà con tự điền biểu mẫu trên trang giúp em nhé — lúc nào muốn em hỗ trợ đọc–điền, "
        "bà con bấm **Xem lại và đồng ý** ạ."
    ),
    "tts": (
        "Dạ em tôn trọng quyết định của bà con. Em sẽ không đọc và không xử lý giấy tờ nào, "
        "bà con tự điền biểu mẫu trên trang nhé. Lúc nào muốn em hỗ trợ, bà con bấm xem lại và đồng ý ạ."
    ),
}

CONSENT_RESHOW = {
    "md": "Dạ, bà con đọc lại nội dung xin phép dưới đây rồi xác nhận giúp em ạ:",
    "tts": "Dạ, bà con đọc lại nội dung xin phép rồi xác nhận giúp em ạ.",
}

CONSENT_REMIND = {
    "md": (
        "Dạ bà con xác nhận **thẻ xin phép xử lý dữ liệu** bên trên giúp em ạ — "
        "đồng ý thì tích 2 ô rồi bấm **Đồng ý và tự động điền**, "
        "không thì chọn **Không đồng ý · Tự nhập** nhé."
    ),
    "tts": (
        "Dạ bà con xác nhận thẻ xin phép bên trên giúp em ạ. Đồng ý thì tích hai ô rồi bấm "
        "đồng ý và tự động điền, không thì chọn tự nhập nhé."
    ),
}

QR_WAITING = {
    "md": (
        "Dạ bà con chọn **📱 Gửi giấy tờ qua điện thoại** ✓\n\n"
        "Mời bà con mở **camera điện thoại**, quét **mã QR** dưới đây — "
        "điện thoại sẽ hiện trang chụp ảnh giấy tờ ạ."
    ),
    "tts": "Mời bà con mở camera điện thoại rồi quét mã QR trên màn hình để tải ảnh giấy tờ lên ạ.",
}

MOBILE_CONNECTED = {
    "md": (
        "📱 Điện thoại đã kết nối ✓ Bà con **chụp lần lượt** theo danh sách trên điện thoại "
        "(CCCD chụp cả 2 mặt), hoặc **chọn nhiều ảnh có sẵn** — em tự nhận dạng và cập nhật "
        "tiến trình ngay tại đây ạ."
    ),
    "tts": (
        "Điện thoại đã kết nối rồi ạ. Bà con chụp lần lượt từng giấy tờ theo danh sách, "
        "căn cước chụp cả hai mặt. Em sẽ báo ngay khi nhận được từng ảnh ạ."
    ),
}

MOBILE_CONNECTED_ATTACH = {
    "md": (
        "📱 Điện thoại đã kết nối ✓ Bà con chụp hoặc chọn tất cả **giấy tờ cần chứng thực bản sao**. "
        "xong bà con bấm **Gửi tất cả** trên điện thoại ạ."
    ),
    "tts": (
        "Điện thoại đã kết nối rồi ạ. Bà con chụp hoặc chọn tất cả giấy tờ cần chứng thực bản sao, "
        "Xong bà con bấm gửi tất cả nhé."
    ),
}

# Chỉ nói SỐ ĐÃ NHẬN, không "x/y" — tổng gồm slot tuỳ chọn dễ làm bà con tưởng còn thiếu.
DOCS_COMPLETE_NEXT_STEP = {
    "md": (
        "✅ Em đã nhận **{files_count} tệp giấy tờ** theo phiên **{sid}**.\n\n"
        "Em đang **tự đọc (OCR)** và chuẩn bị điền vào form bên trái — "
        "khoảng nửa phút, bà con chờ em chút nhé…"
    ),
    "tts": (
        "Em đã nhận {files_count} tệp giấy tờ. "
        "Em đang tự đọc và chuẩn bị điền vào form bên trái, khoảng nửa phút, bà con chờ em chút nhé."
    ),
}

DOCS_COMPLETE_ATTACH = {
    "md": (
        "✅ Em đã nhận **{files_count} tệp giấy tờ** theo phiên **{sid}**.\n\n"
        "Em đang chuẩn bị đính tất cả tệp vào **cùng một hồ sơ**, bà con chờ em chút ạ…"
    ),
    "tts": (
        "Em đã nhận {files_count} tệp giấy tờ. Em đang chuẩn bị đính tất cả tệp vào cùng một hồ sơ, "
        "bà con chờ em chút ạ."
    ),
}

DOCS_FORCED_MISSING = {
    "md": (
        "Dạ bà con chốt gửi với **{files_count} tệp**. Em vẫn đọc và điền phần có được; "
        "thiếu thông tin nào em sẽ hỏi lại ạ. Đang xử lý, bà con chờ chút…"
    ),
    "tts": (
        "Dạ bà con chốt gửi với {files_count} tệp. Em vẫn đọc và điền phần có được, "
        "thiếu thông tin nào em sẽ hỏi lại ạ. Đang xử lý bà con chờ chút nhé."
    ),
}

FILL_READY = {
    "md": (
        "Xong rồi ạ! Em đã đọc được **{count} trường thông tin** và đang điền vào form bên trái. "
        "Bà con nhìn sang form **kiểm tra lại** giúp em nhé — ô viền **vàng** là em đặt mặc định, "
        "ô viền **đỏ** là còn thiếu."
    ),
    "tts": (
        "Em đã đọc được {count} trường thông tin và đang điền vào form bên trái. "
        "Bà con nhìn sang form kiểm tra lại giúp em nhé. Ô viền vàng là em đặt mặc định, "
        "ô viền đỏ là còn thiếu ạ."
    ),
}

FILL_REPORT_REVIEW = {
    "md": (
        "Em điền được **{filled} ô** ✓{missing_note}\n\n"
        "Bà con rà lại trên form, sửa trực tiếp ô nào chưa đúng. Sau đó chuyển qua trang thành phần hồ sơ, rồi bấm "
        "**Đính kèm giấy tờ** để em gắn ảnh giấy tờ vào hồ sơ ạ."
    ),
    "tts": (
        "Em điền xong {filled} ô rồi ạ. Bà con rà lại trên form, "
        "xong bấm Đính kèm giấy tờ để em gắn giấy tờ vào hồ sơ nhé."
    ),
}

PIPELINE_ERROR = {
    "md": (
        "⚠️ Em gặp lỗi khi đọc giấy tờ: *{error}*\n\n"
        "Bà con bấm **thử lại** giúp em, hoặc chụp lại giấy tờ rõ hơn ạ."
    ),
    "tts": "Em gặp lỗi khi đọc giấy tờ bà con bấm thử lại giúp em nhé.",
}

ATTACH_PIPELINE_ERROR = {
    "md": (
        "⚠️ Em gặp lỗi khi chuẩn bị đính kèm giấy tờ: *{error}*\n\n"
        "Các tệp đã nhận vẫn còn trong phiên; bà con bấm **thử lại** giúp em ạ."
    ),
    "tts": "Em gặp lỗi khi chuẩn bị đính kèm. Các tệp vẫn còn, bà con bấm thử lại giúp em nhé.",
}

ATTACH_PLANNING = {
    "md": "Dạ, em đang **lập kế hoạch đính kèm** giấy tờ vào thành phần hồ sơ, chờ em chút ạ…",
    "tts": "Em đang lập kế hoạch đính kèm giấy tờ, bà con chờ chút ạ.",
}

ATTACH_PLAN_READY = {
    "md": (
        "📎 Kế hoạch đính kèm đã xong — **{count} mục**:\n\n{plan_list}\n\n"
        "Em đang **tự đính từng tệp** vào thành phần hồ sơ trên trang, bà con chờ chút ạ…"
    ),
    "tts": "Kế hoạch đính kèm xong rồi, {count} mục. Em đang tự đính từng tệp vào hồ sơ, bà con chờ chút ạ.",
}

# Đòi đính kèm khi trang còn ở bước kê khai (wizard chưa sang "Thành phần hồ sơ") —
# chạy engine lúc này sẽ ra "0 tệp" vô nghĩa → dặn chuyển bước, sang đến nơi tự đính.
ATTACH_WRONG_PAGE = {
    "md": (
        "Dạ bà con đang ở bước **Kê khai thông tin** ạ. Bà con bấm nút tiếp tục của trang "
        "để chuyển sang bước **Thành phần hồ sơ** — vào đến nơi em **tự đính kèm** giấy tờ ngay ạ."
    ),
    "tts": (
        "Dạ bà con đang ở bước kê khai thông tin ạ. Bà con bấm tiếp tục để chuyển sang "
        "bước thành phần hồ sơ, vào đến nơi em tự đính kèm giấy tờ ngay ạ."
    ),
}

ATTACH_PAGE_REACHED = {
    "md": "Thấy bước **Thành phần hồ sơ** rồi ✓ Em đính kèm giấy tờ vào hồ sơ ngay ạ…",
    "tts": "Thấy bước thành phần hồ sơ rồi ạ. Em đính kèm giấy tờ vào hồ sơ ngay ạ.",
}

ATTACH_NONE = {
    "md": (
        "⚠️ Em chưa gắn được tệp nào vào hồ sơ{error_note}. "
        "Bà con kiểm tra trang đang ở bước **Thành phần hồ sơ** giúp em, rồi bấm **Đính kèm lại** ạ."
    ),
    "tts": (
        "Em chưa gắn được tệp nào vào hồ sơ ạ. Bà con kiểm tra trang đang ở bước "
        "thành phần hồ sơ giúp em, rồi bấm đính kèm lại nhé."
    ),
}

ATTACH_DONE = {
    "md": (
        "✅ Em đã đính xong **{attached} tệp** vào thành phần hồ sơ.\n\n"
        "Bà con **rà lại lần cuối** trên trang rồi bấm **Nộp hồ sơ / Gửi hồ sơ** giúp em ạ — "
        "bước nộp cuối em để bà con tự bấm cho chắc chắn."
    ),
    "tts": (
        "Em đã đính xong {attached} tệp vào hồ sơ rồi ạ. "
        "Bà con rà lại lần cuối rồi bấm nộp hồ sơ giúp em nhé."
    ),
}

ATTACH_DONE_WITH_ERRORS = {
    "md": (
        "⚠️ Em đính được **{attached} tệp**, còn lỗi:\n\n{error_list}\n\n"
        "Bà con đính tay phần còn thiếu (nút *Chọn tệp đính kèm* trên trang) rồi bấm **Nộp hồ sơ** giúp em ạ."
    ),
    "tts": "Em đính được {attached} tệp, còn vài mục lỗi. Bà con đính tay phần còn thiếu rồi nộp hồ sơ giúp em ạ.",
}

SCAN_PICK = {
    "md": (
        "Dạ bà con chọn **📷 Scan tại quầy** ✓\n\n"
        "Bà con đặt giấy tờ lên máy scan (hoặc đã có sẵn ảnh/PDF trong máy tính), "
        "rồi **chọn tệp** trong cửa sổ vừa mở — chọn nhiều tệp một lần cũng được, "
        "em tự nhận dạng và phân loại ạ."
    ),
    "tts": (
        "Dạ, bà con đặt giấy tờ lên máy scan rồi chọn tệp từ máy tính trong cửa sổ vừa mở nhé. "
        "Chọn nhiều tệp một lần cũng được, em tự phân loại ạ."
    ),
}

SCAN_PICK_ATTACH = {
    "md": (
        "Dạ bà con chọn **📷 Scan tại quầy** ✓\n\n"
        "Bà con đặt giấy tờ lên máy scan hoặc chọn ảnh/PDF có sẵn trong máy tính. Có thể chọn "
        "**nhiều tệp một lần**; tất cả được nhận thẳng là **Giấy tờ cần chứng thực bản sao**, "
        "không phân loại ở bước tải lên ạ."
    ),
    "tts": (
        "Bà con chọn scan tại quầy ạ. Bà con chọn một hoặc nhiều tệp trong máy tính. "
    ),
}

PROFILE_ASK_PHONE = {
    "md": (
        "Dạ bà con chọn **📁 Lấy dữ liệu đã lưu** ✓\n\n"
        "Bà con đọc/nhập **số điện thoại** đã dùng để lưu hồ sơ lần trước giúp em ạ."
    ),
    "tts": "Bà con đọc số điện thoại đã dùng để lưu hồ sơ lần trước giúp em ạ.",
}

PROFILE_NOT_FOUND = {
    "md": (
        "Dạ em **chưa tìm thấy hồ sơ đã lưu** với số **{phone}** ạ. "
        "Bà con kiểm tra lại số, hoặc chọn cách khác bên dưới nhé:"
    ),
    "tts": "Em chưa tìm thấy hồ sơ đã lưu với số này ạ. Bà con kiểm tra lại số hoặc chọn cách khác nhé.",
}

PROFILE_APPLIED = {
    "md": (
        "✅ Em tìm thấy **hồ sơ đã lưu** của bà con ({count} giấy tờ) — không phải chụp lại gì cả!\n\n"
        "Em bắt đầu **đọc và điền vào form** luôn nhé, bà con chờ chút ạ…"
    ),
    "tts": "Em tìm thấy hồ sơ đã lưu của bà con rồi, không phải chụp lại gì cả. Em điền vào form luôn nhé.",
}

DONE_SUBMITTED = {
    "md": (
        "🎉 **Hồ sơ đã nộp thành công!** Chúc mừng bà con ạ.\n\n"
        "Bà con để lại **số điện thoại** để em báo **tiến độ & kết quả** nhé. "
        "Và nếu muốn, em **lưu hồ sơ** để lần sau không phải chụp lại giấy tờ — "
        "dữ liệu thuộc quyền bà con, **xoá được bất cứ lúc nào**."
    ),
    "tts": (
        "Hồ sơ đã nộp thành công, chúc mừng bà con! Bà con để lại số điện thoại để em báo tiến độ nhé. "
        "Em cũng có thể lưu hồ sơ để lần sau không phải chụp lại, xoá được bất cứ lúc nào ạ."
    ),
}

PHONE_SUBSCRIBED = {
    "md": "✅ Em đã ghi nhận số **{phone}** — có tiến độ mới em nhắn bà con ngay ạ.",
    "tts": "Em đã ghi nhận số điện thoại, có tiến độ mới em nhắn bà con ngay ạ.",
}

PHONE_INVALID = {
    "md": "Dạ số **{phone}** chưa đúng định dạng ạ — bà con đọc lại 10 số bắt đầu bằng 0 giúp em nhé.",
    "tts": "Dạ số này chưa đúng, bà con đọc lại mười số bắt đầu bằng số không giúp em nhé.",
}


PROFILE_NEED_PHONE = {
    "md": "Dạ, để **lưu hồ sơ** bà con cho em xin **số điện thoại** làm chìa khoá tra cứu ạ.",
    "tts": "Để lưu hồ sơ, bà con cho em xin số điện thoại làm chìa khoá tra cứu ạ.",
}

PROFILE_SAVED = {
    "md": (
        "💾 Đã **lưu hồ sơ** theo số **{phone}** ({count} giấy tờ). "
        "Lần sau bà con chỉ cần chọn **📁 Lấy dữ liệu đã lưu** + đọc số này là xong ạ.\n\n"
        "🔒 Muốn xoá lúc nào, bà con bấm **🗑️ Xóa dữ liệu** hoặc nói \"xoá hồ sơ của tôi\"."
    ),
    "tts": "Đã lưu hồ sơ theo số điện thoại của bà con. Lần sau chỉ cần đọc số này là không phải chụp lại giấy tờ ạ.",
}

DATA_DELETED = {
    "md": "🗑️ Em đã **xoá toàn bộ** dữ liệu: hồ sơ đã lưu, ảnh giấy tờ và phiên làm việc. Cảm ơn bà con đã sử dụng ạ!",
    "tts": "Em đã xoá toàn bộ dữ liệu của bà con. Cảm ơn bà con đã sử dụng ạ.",
}

CHANGED_LOCATION = {
    "md": "Dạ, em đã chọn nơi làm thủ tục thành **{ward}, {province}** ✓",
    "tts": "Em đã chọn nơi làm thủ tục thành {ward}, {province}.",
}

CHANGED_PROCEDURE_RESET = {
    "md": "Dạ, mình đổi sang thủ tục khác nhé. Bà con chọn thủ tục bên dưới ạ:",
    "tts": "Dạ, mình đổi sang thủ tục khác. Bà con chọn thủ tục ạ.",
}

OFF_SCOPE = {
    "md": (
        "Dạ, câu này nằm ngoài phạm vi em được đào tạo ạ 🙏 "
        "Em hỗ trợ được **{count} thủ tục**: {procedures}. Bà con cần làm thủ tục nào ạ?"
    ),
    "tts": "Dạ, câu này ngoài phạm vi em hỗ trợ ạ. Bà con cần làm thủ tục nào trong danh sách ạ?",
}

FALLBACK_CLARIFY = {
    "md": "Dạ bà con nói rõ hơn giúp em với ạ — bà con muốn **{hint}** phải không ạ?",
    "tts": "Dạ bà con nói rõ hơn giúp em với ạ.",
}

# Nhãn bước hiển thị trên thanh tiến trình (progress.label) — khớp docs/03a §3.
STEP_LABELS = {
    "greet": "Chọn thủ tục",
    "confirm_procedure": "Xác nhận thủ tục",
    "guide_login": "Đăng nhập VNeID",
    "consent": "Xin phép xử lý dữ liệu",
    "ask_doc_method": "Cách cung cấp giấy tờ",
    "qr_waiting": "Quét mã QR",
    "collecting_docs": "Gửi giấy tờ",
    "filling": "Điền hồ sơ",
    "reviewing": "Rà soát",
    "attaching": "Đính kèm",
    "done": "Hoàn thành",
}

# Thứ tự bước cho progress.step (1-based).
STEP_ORDER = [
    "greet", "confirm_procedure", "guide_login", "consent", "ask_doc_method",
    "qr_waiting", "collecting_docs", "filling", "reviewing", "attaching", "done",
]
