"""Nguyên văn nội dung đã hiển thị cho chủ thể dữ liệu, để biên bản chấp thuận chép lại ĐỦ chữ.

Auto Fill: extension tải nội dung thẻ từ GET /api/v1/consent/notice (bản AUTOFILL_CURRENT_VERSION) và gửi lại đúng
`version` đó khi đồng ý → BE tra bản sao nguyên văn theo phiên bản. Bản extension cũ trên chợ vẫn hiện thẻ viết cứng
trong popup.html và gửi version của nó (v1.1). Sửa chữ thẻ = thêm bản MỚI vào AUTOFILL_NOTICES rồi trỏ
AUTOFILL_CURRENT_VERSION sang bản đó; KHÔNG sửa bản đã có (biên bản của log cũ phải đúng chữ đã hiển thị).
Handfree: thẻ do BE gửi xuống (chat/script_vi.py) → chụp nguyên văn vào bản ghi ngay lúc ghi nhận (consent.build_entry).
Chữ đậm trên thẻ ghi bằng **…**, biên bản giữ nguyên cách nhấn.
"""

# Toàn văn Điều 4 Luật số 91/2025/QH15 — cả hai thẻ đều cho xem đầy đủ (popup.html view-legal, script_vi.CONSENT_LEGAL_MD).
LEGAL_SOURCE = "Theo Luật số 91/2025/QH15 ngày 26/6/2025 — Luật Bảo vệ dữ liệu cá nhân"
LEGAL_ARTICLE_TITLE = "Điều 4. Quyền và nghĩa vụ của chủ thể dữ liệu cá nhân"
# (khoản, [điểm]) — khoản không có điểm thì danh sách rỗng.
LEGAL_ARTICLE_4: list[tuple[str, list[str]]] = [
    ("1. Quyền của chủ thể dữ liệu cá nhân bao gồm:", [
        "a) Được biết về hoạt động xử lý dữ liệu cá nhân;",
        "b) Đồng ý hoặc không đồng ý, yêu cầu rút lại sự đồng ý cho phép xử lý dữ liệu cá nhân;",
        "c) Xem, chỉnh sửa hoặc yêu cầu chỉnh sửa dữ liệu cá nhân;",
        "d) Yêu cầu cung cấp, xóa, hạn chế xử lý dữ liệu cá nhân; gửi yêu cầu phản đối xử lý dữ liệu cá nhân;",
        "đ) Khiếu nại, tố cáo, khởi kiện, yêu cầu bồi thường thiệt hại theo quy định của pháp luật;",
        "e) Yêu cầu cơ quan có thẩm quyền hoặc cơ quan, tổ chức, cá nhân liên quan đến xử lý dữ liệu cá nhân thực hiện "
        "các biện pháp, giải pháp bảo vệ dữ liệu cá nhân của mình theo quy định của pháp luật.",
    ]),
    ("2. Nghĩa vụ của chủ thể dữ liệu cá nhân bao gồm:", [
        "a) Tự bảo vệ dữ liệu cá nhân của mình;",
        "b) Tôn trọng, bảo vệ dữ liệu cá nhân của người khác;",
        "c) Cung cấp đầy đủ, chính xác dữ liệu cá nhân của mình theo quy định của pháp luật, theo hợp đồng hoặc khi "
        "đồng ý cho phép xử lý dữ liệu cá nhân của mình;",
        "d) Chấp hành pháp luật về bảo vệ dữ liệu cá nhân và tham gia phòng, chống hoạt động xâm phạm dữ liệu cá nhân.",
    ]),
    ("3. Chủ thể dữ liệu cá nhân khi thực hiện quyền và nghĩa vụ của mình phải tuân thủ đầy đủ các nguyên tắc sau đây:", [
        "a) Thực hiện theo quy định của pháp luật; tuân thủ nghĩa vụ của chủ thể dữ liệu cá nhân theo hợp đồng. Việc "
        "thực hiện quyền và nghĩa vụ của chủ thể dữ liệu cá nhân phải nhằm mục đích bảo vệ quyền, lợi ích hợp pháp của "
        "chính chủ thể dữ liệu cá nhân đó;",
        "b) Không được gây khó khăn, cản trở việc thực hiện quyền, nghĩa vụ pháp lý của bên kiểm soát dữ liệu cá nhân, "
        "bên kiểm soát và xử lý dữ liệu cá nhân, bên xử lý dữ liệu cá nhân;",
        "c) Không được xâm phạm đến quyền, lợi ích hợp pháp của Nhà nước, cơ quan, tổ chức và cá nhân khác.",
    ]),
    ("4. Cơ quan, tổ chức, cá nhân có trách nhiệm tạo điều kiện thuận lợi, không được gây khó khăn, cản trở việc thực "
     "hiện quyền và nghĩa vụ của chủ thể dữ liệu cá nhân theo quy định của pháp luật.", []),
    ("5. Khi nhận được yêu cầu của chủ thể dữ liệu cá nhân để thực hiện quyền của chủ thể dữ liệu cá nhân quy định tại "
     "khoản 1 Điều này, bên kiểm soát dữ liệu cá nhân, bên kiểm soát và xử lý dữ liệu cá nhân phải kịp thời thực hiện "
     "trong thời hạn theo quy định của pháp luật.", []),
]

# Thẻ xác nhận Auto Fill theo CONSENT_VERSION của popup.js. "{procedure}" = tên thủ tục trong ngoặc kép như popup
# dựng (openConsent), không có tên thì "của thủ tục này".
AUTOFILL_NOTICES: dict[str, dict] = {
    "v1.1": {
        "title": "Cho phép Trợ lý đọc giấy tờ và tự động điền biểu mẫu",
        "intro": (
            "Chỉ khi bạn chọn **“Đồng ý và tự động điền”**, hệ thống **Trợ lý nhân dân** mới đọc, trích xuất và xử lý "
            "thông tin cần thiết từ các giấy tờ dưới đây, sau đó tự động điền vào biểu mẫu **{procedure}**."
        ),
        "documents_title": "Giấy tờ Trợ lý sẽ đọc trong thủ tục này:",
        "documents": [
            "Giấy tờ tùy thân (căn cước công dân/căn cước) của người liên quan trong hồ sơ",
            "Giấy tờ hộ tịch, giấy tờ phù hợp với thủ tục đang thực hiện",
            "Các tài liệu khác bạn chủ động tải lên cho hồ sơ này",
        ],
        "scope": (
            "Trợ lý chỉ đọc những thông tin cần thiết từ giấy tờ bạn chủ động cung cấp để thực hiện thủ tục này. "
            "Bạn có thể kiểm tra, chỉnh sửa dữ liệu trước khi nộp hồ sơ."
        ),
        "purpose": (
            "**Mục đích xử lý dữ liệu:** OCR, chuẩn hoá, hỗ trợ điền biểu mẫu và chuẩn bị tệp đính kèm trên "
            "Cổng Dịch vụ công."
        ),
        "statements": [
            "Tôi đã đọc, hiểu phạm vi giấy tờ, thông tin được xử lý và mục đích nêu trên; đồng ý cho Trợ lý nhân dân "
            "đọc, xử lý và tự động điền dữ liệu vào biểu mẫu.",
            "Tôi xác nhận tự chịu trách nhiệm về tính chính xác, hợp pháp của các thông tin nêu trên và về việc thực "
            "hiện thủ tục hành chính của mình.",
        ],
        "optional_statement": (
            "Khi hệ thống điền bị lỗi hoặc thiếu sót, tôi đồng ý cho Trợ lý lưu lại dữ liệu của lần xử lý này để phân "
            "tích, cải thiện và tối ưu hệ thống."
        ),
        "accept_label": "Đồng ý và tự động điền",
        "decline_label": "Không đồng ý · Tự nhập",
    },
}


# v1.2 = v1.1 + khối "Xử lý tự động bằng AI" đặt dưới mục đích xử lý (popup.html .cs-ai).
AUTOFILL_NOTICES["v1.2"] = {
    **AUTOFILL_NOTICES["v1.1"],
    "automated_title": "**Xử lý tự động bằng trí tuệ nhân tạo (AI):**",
    "automated": [
        "Dữ liệu được xử lý trên hệ thống một cách tự động.",
        "**Nguyên tắc hoạt động:** Trợ lý dùng công nghệ nhận dạng chữ (OCR) để đọc giấy tờ bạn cung cấp. Sau đó mô "
        "hình trí tuệ nhân tạo trích ra những thông tin biểu mẫu của thủ tục cần và tự điền sẵn vào biểu mẫu trên "
        "Cổng Dịch vụ công. Trợ lý chỉ điền sẵn, không quyết định kết quả hồ sơ. Cán bộ và người dân kiểm tra, sửa "
        "trước khi nộp; việc giải quyết hồ sơ do cơ quan có thẩm quyền thực hiện.",
        "**Ảnh hưởng đối với quyền và lợi ích hợp pháp của chủ thể dữ liệu:** việc xử lý tự động không làm thay đổi "
        "quyền, lợi ích hợp pháp của bạn; kết quả đọc tự động có thể sai sót nên cần kiểm tra trước khi nộp.",
        "**Quyền lựa chọn:** bạn có thể chọn dùng hoặc không dùng Trợ lý nhân dân; không dùng thì bấm **“Không đồng "
        "ý · Tự nhập”** và tự nhập trên Cổng Dịch vụ công như bình thường.",
        "**Chỉnh sửa, ẩn danh, xoá dữ liệu:** bạn có quyền yêu cầu chỉnh sửa, ẩn danh hoặc xoá hồ sơ nhận dạng của "
        "mình đã lưu trên hệ thống, kể cả lịch sử xử lý, bằng cách đề nghị cán bộ tiếp nhận.",
    ],
}

# Bản thẻ Auto Fill đang hiển thị cho extension đọc nội dung từ BE.
AUTOFILL_CURRENT_VERSION = "v1.2"


def current_autofill_notice() -> dict:
    """Nội dung thẻ cho extension dựng (chưa thay tên thủ tục — extension thay "{procedure}" như autofill_notice)."""
    return {"version": AUTOFILL_CURRENT_VERSION, "notice": AUTOFILL_NOTICES[AUTOFILL_CURRENT_VERSION]}


def autofill_notice(version: str, procedure_label: str | None) -> dict | None:
    """Nguyên văn thẻ Auto Fill đã hiển thị; phiên bản không có bản lưu → None (biên bản ghi rõ là không có)."""
    notice = AUTOFILL_NOTICES.get(str(version or ""))
    if not notice:
        return None
    procedure = f"“{procedure_label}”" if procedure_label else "của thủ tục này"
    return {**notice, "intro": notice["intro"].format(procedure=procedure)}
